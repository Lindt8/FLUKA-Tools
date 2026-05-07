import re
import sublime
import sublime_plugin

FIELD_WIDTH = 10
CARD_RE = re.compile(r"[^\s*]+")  # non-whitespace token, excluding '*' as a card starter


def _col_to_field_end(col0):
    """Return zero-based inclusive end column of the field containing col0."""
    return ((col0 // FIELD_WIDTH) + 1) * FIELD_WIDTH - 1


def _col_to_field_start(col0):
    """Return zero-based start column of the field containing col0."""
    return (col0 // FIELD_WIDTH) * FIELD_WIDTH


def _next_field_start(col0):
    return ((col0 // FIELD_WIDTH) + 1) * FIELD_WIDTH


def _prev_field_start(col0):
    return max(0, ((col0 - 1) // FIELD_WIDTH) * FIELD_WIDTH)


class FlukaSmartTabCommand(sublime_plugin.TextCommand):
    """FLUKA-aware Tab / Shift-Tab behavior for fixed 10-character fields.

    Modes:
      right:       Tab. Align the current/next token rightward within its current field.
                   If already right-aligned, insert 10 spaces before it.
                   If no token follows cursor, fall back to boundary jump.

      left:        Shift+Tab. Move the current/next token left by deleting spaces before it
                   until it is right-aligned in the field containing its first character.

      right_eat:   Option+Tab. Same target as right, but for each space inserted before the
                   token, remove one whitespace character after the token. This preserves the
                   positions of text farther to the right when possible. Conservative: if there
                   is not enough whitespace after the token, do nothing.

      left_fill:   Option+Shift+Tab. Same target as left, but inserts the same number of spaces
                   after the token as were deleted before it. This preserves text farther right.
    """

    def run(self, edit, mode="right"):
        # Process bottom-to-top so edits earlier in the buffer do not disturb later selections.
        for sel in reversed(list(self.view.sel())):
            if not sel.empty():
                self.view.erase(edit, sel)
                point = sel.begin()
            else:
                point = sel.begin()

            if mode == "right":
                self._right(edit, point, eat_right=False)
            elif mode == "right_eat":
                self._right(edit, point, eat_right=True)
            elif mode == "left":
                self._left(edit, point, fill_right=False)
            elif mode == "left_fill":
                self._left(edit, point, fill_right=True)
            else:
                self._fallback_next_boundary(edit, point)

    def _line_info(self, point):
        line_region = self.view.line(point)
        line_text = self.view.substr(line_region)
        row, col0 = self.view.rowcol(point)
        return line_region, line_text, col0

    def _find_card_at_or_after_cursor(self, line_text, col0):
        """Find token to operate on.

        If cursor is inside a token, return that whole token. Otherwise skip whitespace
        to the next token. A token beginning with '*' is not treated as an input card.
        Returns (start_col, end_col_exclusive) or None.
        """
        n = len(line_text)
        c = min(col0, n)

        # If cursor is inside or immediately after a token character, walk left to token start.
        # This handles the requested "cursor in the middle of a card" behavior. We do not treat
        # column-1 '*' comment lines as cards.
        if n and c > 0 and c <= n and not line_text[c - 1].isspace():
            start = c - 1
            while start > 0 and not line_text[start - 1].isspace():
                start -= 1
            end = start
            while end < n and not line_text[end].isspace():
                end += 1
            if line_text[start:end].startswith("*"):
                return None
            return start, end

        # Otherwise skip whitespace to next token.
        while c < n and line_text[c].isspace():
            c += 1
        if c >= n:
            return None
        if line_text[c] == "*":
            return None
        start = c
        end = start
        while end < n and not line_text[end].isspace():
            end += 1
        return start, end

    def _fallback_next_boundary(self, edit, point):
        col0 = self.view.rowcol(point)[1]
        spaces = FIELD_WIDTH - (col0 % FIELD_WIDTH)
        if spaces == 0:
            spaces = FIELD_WIDTH
        self.view.insert(edit, point, " " * spaces)
        self.view.sel().clear()
        self.view.sel().add(sublime.Region(point + spaces))

    def _right(self, edit, point, eat_right=False):
        line_region, line_text, col0 = self._line_info(point)
        found = self._find_card_at_or_after_cursor(line_text, col0)
        if found is None:
            self._fallback_next_boundary(edit, point)
            return

        start, end = found
        # If current character after cursor is whitespace and the found token starts later,
        # insert at token start, not at cursor. If cursor was inside token, start is token start.
        insert_point = line_region.begin() + start
        end_col_inclusive = end - 1
        current_field_end = _col_to_field_end(end_col_inclusive)
        spaces = current_field_end - end_col_inclusive
        if spaces == 0:
            spaces = FIELD_WIDTH

        if eat_right:
            after = line_text[end:end + spaces]
            if len(after) < spaces or any(not ch.isspace() for ch in after):
                return
            # Delete after-token whitespace first, then insert before token.
            self.view.erase(edit, sublime.Region(line_region.begin() + end, line_region.begin() + end + spaces))
            self.view.insert(edit, insert_point, " " * spaces)
        else:
            self.view.insert(edit, insert_point, " " * spaces)

        new_point = insert_point + spaces
        self.view.sel().clear()
        self.view.sel().add(sublime.Region(new_point))

    def _left(self, edit, point, fill_right=False):
        line_region, line_text, col0 = self._line_info(point)
        found = self._find_card_at_or_after_cursor(line_text, col0)
        if found is None:
            return

        start, end = found
        if start == 0:
            return

        token_len = end - start
        target_field_end = _col_to_field_end(start)
        target_start = target_field_end - token_len + 1
        # If the token is too long for the field, put its first char at the field start.
        target_start = max(_col_to_field_start(start), target_start)

        remove_spaces = start - target_start
        if remove_spaces <= 0:
            # Already at the computed target. Try to move one full field left if possible.
            previous_field_end = _col_to_field_start(start) - 1
            if previous_field_end < 0:
                return
            target_start = max(_col_to_field_start(previous_field_end), previous_field_end - token_len + 1)
            remove_spaces = start - target_start

        before = line_text[start - remove_spaces:start]
        if len(before) < remove_spaces or any(ch != " " for ch in before):
            return

        # Delete spaces before token. Optionally insert same count after token.
        self.view.erase(edit, sublime.Region(line_region.begin() + start - remove_spaces, line_region.begin() + start))
        if fill_right:
            # After deletion, token end shifts left by remove_spaces.
            new_end = line_region.begin() + end - remove_spaces
            self.view.insert(edit, new_end, " " * remove_spaces)

        new_point = line_region.begin() + target_start
        self.view.sel().clear()
        self.view.sel().add(sublime.Region(new_point))


# Backwards-compatible command name in case an old keymap still calls fluka_tab.
class FlukaTabCommand(FlukaSmartTabCommand):
    pass
