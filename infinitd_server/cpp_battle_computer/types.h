#pragma once

#include <math.h>

struct CppCellPos {
  float row, col;

  CppCellPos() : row(-1.0), col(-1.0) {}
  CppCellPos(float row_, float col_) : row(row_), col(col_) {}

  float distSq(const CppCellPos& other) {
    const float rowDist = this->row - other.row;
    const float colDist = this->col - other.col;
    return rowDist * rowDist + colDist * colDist;
  }

  float dist(const CppCellPos& other) {
    return sqrt(this->distSq(other));
  }
};
