# -*- coding: utf-8 -*-
from __future__ import annotations

from functools import reduce
from itertools import groupby
from operator import ior
from typing import Dict, Generator, Iterator, List, Optional

from hex_forest.common import BitBoard
from hex_forest.common.cell import Cell
from hex_forest.models.move import FakeMove


def generate_masks(bb: BitBoard) -> Iterator:
    while bb:
        r = bb & -bb
        yield r
        bb ^= r


class BoardShapeError(Exception):
    """"""


class Board:
    """"""

    turn: bool
    """The side to move True for white, False for black."""

    move_stack: List[FakeMove]
    """List of moves on board from first to last."""

    occupied_co: Dict[bool, BitBoard]
    unoccupied: BitBoard

    def __init__(self, notation: Optional[str] = None, *, size: int = 13) -> None:
        self.size = size
        self.rows = self.generate_rows(size)

        self.reset_board()

        self.bb_rows: List[BitBoard] = [
            reduce(ior, [1 << (col + row * size) for col in range(size)])
            for row in range(size)
        ]
        self.bb_cols: List[BitBoard] = [
            reduce(ior, [(1 << col) << (row * size) for row in range(size)])
            for col in range(size)
        ]
        self.vertical_coeff = 2 ** self.size
        self.diagonal_coeff = 2 ** (self.size - 1)
        self.reset_board()

        if notation:
            self.initialize_notation(notation)

    def reset_board(self) -> None:
        """"""

        self.turn = False
        self.occupied_co = {False: 0, True: 0}
        self.unoccupied = (1 << self.size**2) - 1
        self.move_stack = []

    def initialize_notation(self, notation: str) -> None:
        """"""

        move_str: str = ""
        color: bool = False
        i = 0
        for is_letter, value in groupby(notation, str.isalpha):
            move_str += "".join(value)
            if not is_letter:
                move = FakeMove.from_coord(i, move_str)
                self.occupied_co[color] |= move.get_mask(self.size)
                self.move_stack.append(move)

                move_str = ""
                color = not color

        self.unoccupied ^= (self.occupied_co[True] | self.occupied_co[False])

        self.turn = color

    @staticmethod
    def generate_rows(size):
        rows = []
        for y in range(size):
            cells = []
            for x in range(size):
                cell = Cell(x, y)
                cells.append(cell)
            rows.append(cells)
        return rows

    def is_game_over(self) -> bool:
        """"""

        return self.winner() is not None

    def winner(self) -> Optional[bool]:
        """"""

        if self.turn and self.is_black_win():  # last move was black
            return False

        elif not self.turn and self.is_white_win():  # last move was white
            return True

        return None

    def is_black_win(self) -> bool:
        """"""

        blacks: BitBoard = self.occupied_co[False]

        # check there is a black stone on every row
        if not all((blacks & row for row in self.bb_rows)):
            return False

        # find connection from top to bottom
        for mask in generate_masks(blacks & self.bb_rows[0]):
            if self.is_connected_to_bottom(mask):
                return True

        return False

    def is_connected_to_bottom(self, mask: BitBoard, visited: BitBoard = 0) -> bool:
        """
        Recurrent way of finding if a stone is connected to bottom.
        """

        if mask & self.bb_rows[self.size - 1]:
            return True

        visited |= mask

        for neighbour in self.generate_neighbours_black(mask, visited):
            if self.is_connected_to_bottom(neighbour, visited):
                return True

        return False

    def generate_neighbours_black(self, mask: BitBoard, visited: BitBoard) -> Iterator:
        """
        Generate in optimized order to find black connection.
        """

        blacks: BitBoard = self.occupied_co[False]

        for f in (
            self.cell_right,
            self.cell_down,
            self.cell_downleft,
            self.cell_left,
            self.cell_upright,
            self.cell_up,
        ):
            try:
                neighbour_cell = f(mask)
            except BoardShapeError:
                continue
            else:
                if neighbour_cell & blacks & ~visited:
                    yield neighbour_cell

    def is_white_win(self) -> bool:
        """"""

        whites: BitBoard = self.occupied_co[True]

        # check there is a white stone on every column
        if not all((whites & col for col in self.bb_cols)):
            return False

        # find connection from left to right
        for mask in generate_masks(whites & self.bb_cols[0]):
            if self.is_connected_to_right(mask):
                return True

        return False

    def is_connected_to_right(self, mask: BitBoard, visited: BitBoard = 0) -> bool:
        """
        Recurrent way of finding if a stone is connected to bottom.
        """

        if mask & self.bb_cols[self.size - 1]:
            return True

        visited |= mask

        for neighbour in self.generate_neighbours_white(mask, visited):
            if self.is_connected_to_right(neighbour, visited):
                return True

        return False

    def generate_neighbours_white(
        self, mask: BitBoard, visited: BitBoard
    ) -> Generator[BitBoard, None, None]:
        """
        Generate in optimized order to find white connection.
        """

        whites: BitBoard = self.occupied_co[True]

        for f in (
            self.cell_down,
            self.cell_right,
            self.cell_upright,
            self.cell_up,
            self.cell_downleft,
            self.cell_left,
        ):
            try:
                neighbour_cell = f(mask)
            except BoardShapeError:
                continue
            else:
                if neighbour_cell & whites & ~visited:
                    yield neighbour_cell

    def cell_right(self, mask: BitBoard) -> BitBoard:
        """"""

        # 0 is the first column on the left
        if mask & self.bb_cols[self.size - 1]:
            raise BoardShapeError(f"trying to shift right {bin(mask)}")

        # cells are ordered opposite direction to bits in bitboard
        return mask << 1

    def cell_left(self, mask: BitBoard) -> BitBoard:
        """"""

        # 0 is the first column on the left
        if mask & self.bb_cols[0]:
            raise BoardShapeError(f"trying to shift left {bin(mask)}")

        # cells are ordered opposite direction to bits in bitboard
        return mask >> 1

    def cell_down(self, mask: BitBoard) -> BitBoard:
        """"""

        # 0 is the first row on top
        if mask & self.bb_rows[self.size - 1]:
            raise BoardShapeError(f"trying to shift down {bin(mask)}")

        return mask << self.size

    def cell_up(self, mask: BitBoard) -> BitBoard:
        """"""

        if mask & self.bb_rows[0]:
            raise BoardShapeError(f"trying to shift down {bin(mask)}")

        return mask >> self.size

    def cell_downleft(self, mask: BitBoard) -> BitBoard:
        """"""

        if mask & self.bb_rows[self.size - 1] or mask & self.bb_cols[0]:
            raise BoardShapeError(f"trying to shift downleft {bin(mask)}")

        return mask << (self.size - 1)

    def cell_upright(self, mask: BitBoard) -> BitBoard:
        """"""

        if mask & self.bb_rows[0] or mask & self.bb_cols[self.size - 1]:
            raise BoardShapeError(f"trying to shift down {bin(mask)}")

        return mask >> (self.size - 1)

    def push_coord(self, coord: str) -> None:
        """"""

        self.push(FakeMove.from_coord(coord, self.size))

    def push(self, move: FakeMove) -> None:
        """"""

        mask = move.get_mask(self.size)
        self.occupied_co[self.turn] |= mask
        self.unoccupied ^= mask

        self.move_stack.append(move)

        self.turn = not self.turn

    def pop(self) -> None:
        """"""

        self.occupied_co[not self.turn] ^= self.move_stack.pop().get_mask(self.size)

        self.turn = not self.turn
