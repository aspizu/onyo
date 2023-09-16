/// Calculate the remainder of left divided by right, ensuring the result has
/// the same sign as right.
pub fn modulo(left: i64, right: i64) -> i64 {
   let mut result = left % right;
   if (result < 0) != (right < 0) {
      result += right;
   }
   result
}

/// Calculate the remainder of left divided by right, ensuring the result has
/// the same sign as right.
pub fn fmodulo(left: f64, right: f64) -> f64 {
   let mut result = left % right;
   if (result < 0.) != (right < 0.) {
      result += right;
   }
   result
}
