#pragma once

#include <math.h>
#include <ostream>

struct CppCellPos {
  float row, col;

  CppCellPos() : row(-1.0), col(-1.0) {}
  CppCellPos(float row_, float col_) : row(row_), col(col_) {}

  float distSq(const CppCellPos& other) const {
    const float rowDist = this->row - other.row;
    const float colDist = this->col - other.col;
    return rowDist * rowDist + colDist * colDist;
  }

  float dist(const CppCellPos& other) const {
    return sqrt(this->distSq(other));
  }

  CppCellPos operator-() const {
    return CppCellPos(-this->row, -this->col);
  }

  CppCellPos operator-(const CppCellPos& in) const {
    return CppCellPos(this->row - in.row, this->col - in.col);
  }

  CppCellPos operator+(const CppCellPos& in) const {
    return CppCellPos(this->row + in.row, this->col + in.col);
  }

  CppCellPos operator*(const float scalar) const {
    return CppCellPos(this->row * scalar, this->col * scalar);
  }
};

std::ostream& operator<< (std::ostream &out, CppCellPos const& pos) {
    out << "(" << pos.row << ", " << pos.col << ")";
    return out;
}