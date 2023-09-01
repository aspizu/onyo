/* A Generic dynamic array template with a Rust's Vector-like API.                    *
 * ---------------------------------------------------------------------------------- *
 * How to use:                                                                        *
 * Use DEFINE_VEC in your header file (.h)                                            *
 * Use IMPL_VEC in your source file (.c)                                              *
 * The name of all functions start with the TYPE_NAME you chose. (Ex. CharVec_new())  */

#define DEFAULT_EQUALS(LEFT, RIGHT) LEFT == RIGHT

/* TYPE_NAME: The name of the type to be defined.
 * TYPE: The type of the elements. */
#define DEFINE_VEC(TYPE_NAME, TYPE)                                                    \
   typedef struct TYPE_NAME TYPE_NAME;                                                 \
   struct TYPE_NAME {                                                                  \
      TYPE * data;                                                                     \
      usize len;                                                                       \
      usize cap;                                                                       \
   };                                                                                  \
   TYPE_NAME TYPE_NAME##_new(void);                                                    \
   void TYPE_NAME##_free(TYPE_NAME * vec);                                             \
   TYPE_NAME TYPE_NAME##_with_capacity(usize cap);                                     \
   void TYPE_NAME##_reserve(TYPE_NAME * vec, usize additional);                        \
   void TYPE_NAME##_reserve_exact(TYPE_NAME * vec, usize additional);                  \
   void TYPE_NAME##_shrink_to_fit(TYPE_NAME * vec);                                    \
   void TYPE_NAME##_remove(TYPE_NAME * vec, usize index);                              \
   void TYPE_NAME##_push(TYPE_NAME * vec, TYPE value);                                 \
   void TYPE_NAME##_clear(TYPE_NAME * vec);                                            \
   usize TYPE_NAME##_index(TYPE_NAME * vec, TYPE item);

/* TYPE_NAME: The name of the type to be defined.
 * TYPE: The type of the elements.
 * EQUALS: A function that compares two elements. For primitive data-types use
 *         DEFAULT_EQUALS which will use the == operator to compare elements. */
#define IMPL_VEC(TYPE_NAME, TYPE, EQUALS)                                              \
   TYPE_NAME TYPE_NAME##_new(void) {                                                   \
      return (TYPE_NAME){.data = NULL, .len = 0, .cap = 0};                            \
   }                                                                                   \
                                                                                       \
   void TYPE_NAME##_free(TYPE_NAME * vec) {                                            \
      if (vec->data != NULL) {                                                         \
         free(vec->data);                                                              \
         vec->data = NULL;                                                             \
      }                                                                                \
      vec->len = 0;                                                                    \
      vec->cap = 0;                                                                    \
   }                                                                                   \
                                                                                       \
   TYPE_NAME TYPE_NAME##_with_capacity(usize cap) {                                    \
      return (TYPE_NAME){.data = malloc(sizeof(TYPE) * cap), .len = 0, .cap = cap};    \
   }                                                                                   \
                                                                                       \
   void TYPE_NAME##_reserve(TYPE_NAME * vec, usize additional) {                       \
      if (!(vec->cap < vec->len + additional) || vec->len + additional == 0) {         \
         return;                                                                       \
      }                                                                                \
      if (vec->cap == 0) {                                                             \
         vec->cap = 1;                                                                 \
      }                                                                                \
      while (vec->cap < vec->len + additional) {                                       \
         vec->cap *= 2;                                                                \
      }                                                                                \
      if (vec->data == NULL) {                                                         \
         vec->data = malloc(sizeof(TYPE) * vec->cap);                                  \
      } else {                                                                         \
         vec->data = realloc(vec->data, sizeof(TYPE) * vec->cap);                      \
      }                                                                                \
   }                                                                                   \
                                                                                       \
   void TYPE_NAME##_reserve_exact(TYPE_NAME * vec, usize additional) {                 \
      if (!(vec->cap < vec->len + additional) || vec->len + additional == 0) {         \
         return;                                                                       \
      }                                                                                \
      vec->cap = vec->len + additional;                                                \
      if (vec->data == NULL) {                                                         \
         vec->data = malloc(sizeof(TYPE) * vec->cap);                                  \
      } else {                                                                         \
         vec->data = realloc(vec->data, sizeof(TYPE) * vec->cap);                      \
      }                                                                                \
   }                                                                                   \
                                                                                       \
   void TYPE_NAME##_shrink_to_fit(TYPE_NAME * vec) {                                   \
      if (vec->len == vec->cap) {                                                      \
         return;                                                                       \
      }                                                                                \
      vec->cap = vec->len;                                                             \
      if (vec->len == 0) {                                                             \
         if (vec->data != NULL) {                                                      \
            free(vec->data);                                                           \
            vec->data = NULL;                                                          \
         }                                                                             \
         return;                                                                       \
      }                                                                                \
      vec->data = realloc(vec->data, sizeof(TYPE) * vec->cap);                         \
   }                                                                                   \
                                                                                       \
   void TYPE_NAME##_remove(TYPE_NAME * vec, usize index) {                             \
      IF_DEBUG {                                                                       \
         if (index >= vec->len) {                                                      \
            PANIC("Vector index out of bounds: %lu\n", index);                         \
         }                                                                             \
      }                                                                                \
      if (index == vec->len - 1) {                                                     \
         vec->len--;                                                                   \
         return;                                                                       \
      }                                                                                \
      memcpy(                                                                          \
          vec->data + index,                                                           \
          vec->data + index + 1,                                                       \
          sizeof(TYPE) * (vec->len - index - 1)                                        \
      );                                                                               \
      vec->len--;                                                                      \
   }                                                                                   \
                                                                                       \
   void TYPE_NAME##_push(TYPE_NAME * vec, TYPE value) {                                \
      if (vec->len == vec->cap) {                                                      \
         if (vec->data == NULL) {                                                      \
            vec->data = malloc(sizeof(TYPE));                                          \
            vec->cap = 1;                                                              \
         } else {                                                                      \
            vec->cap *= 2;                                                             \
            vec->data = realloc(vec->data, sizeof(TYPE) * vec->cap);                   \
         }                                                                             \
      }                                                                                \
      vec->data[vec->len] = value;                                                     \
      vec->len++;                                                                      \
   }                                                                                   \
                                                                                       \
   void TYPE_NAME##_clear(TYPE_NAME * vec) {                                           \
      vec->len = 0;                                                                    \
   }                                                                                   \
                                                                                       \
   usize TYPE_NAME##_index(TYPE_NAME * vec, TYPE item) {                               \
      for (usize i = 0; i < vec->len; i++) {                                           \
         if (EQUALS(vec->data[i], item)) {                                             \
            return i;                                                                  \
         }                                                                             \
      }                                                                                \
      return vec->len;                                                                 \
   }
