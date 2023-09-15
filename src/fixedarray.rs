use std::{
   convert::From,
   iter::Iterator,
   ops::{Index, IndexMut}
};

struct FixedArray<T> {
   data: Vec<T>,
   width: usize
}

impl<'a, T> FixedArray<T> {
   fn get(&self, index: usize) -> Option<&[T]> {
      if index < (self.data.len() / self.width) {
         Some(&self[index])
      } else {
         None
      }
   }

   fn iter(&'a self) -> FixedArrayIterator<'a, T> {
      return FixedArrayIterator { inner: self, i: 0 };
   }
}

impl<T> Index<usize> for FixedArray<T> {
   type Output = [T];

   fn index(&self, i: usize) -> &Self::Output {
      let i = i * self.width;
      &self.data[i..i + self.width]
   }
}

impl<T> IndexMut<usize> for FixedArray<T> {
   fn index_mut(&mut self, i: usize) -> &mut [T] {
      let i = i * self.width;
      &mut self.data[i..i + self.width]
   }
}

struct FixedArrayIterator<'a, T> {
   inner: &'a FixedArray<T>,
   i: usize
}

impl<'a, T> IntoIterator for &'a FixedArray<T> {
   type IntoIter = FixedArrayIterator<'a, T>;
   type Item = &'a [T];

   fn into_iter(self) -> Self::IntoIter {
      self.iter()
   }
}

impl<'a, T> Iterator for FixedArrayIterator<'a, T> {
   type Item = &'a [T];

   fn next(&mut self) -> Option<Self::Item> {
      let result = self.inner.get(self.i);
      self.i += 1;
      result
   }
}

impl From<Vec<&str>> for FixedArray<u8> {
   fn from(vec: Vec<&str>) -> Self {
      let width = vec.iter().map(|v| v.len()).max().unwrap();
      let data = Vec::with_capacity(width * vec.len());
      let mut new = Self { data, width };
      for item in vec {
         let mut i = 0;
         for c in item.as_bytes() {
            new.data.push(*c);
            i += 1;
         }
         for _ in 0..(width - i) {
            new.data.push(0);
         }
      }
      new
   }
}

fn foo() {
   let s = vec!["one", "two", "three", "four", "five"];
   let a = FixedArray::<u8>::from(s);
   for i in &a {
      println!("{}", std::str::from_utf8(i).unwrap().trim_end_matches('\0'));
   }
}
