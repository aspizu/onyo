#define DEBUG true

#include "vec.h"

#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define PANIC(...)                                                                     \
   fprintf(stderr, __VA_ARGS__);                                                       \
   exit(1)
#define IF_DEBUG if (DEBUG)
#define CHILD(INDEX) ->children.data[INDEX]
#define DEFINE_RESULT_TYPE(TYPE_NAME, MEMBERS)                                         \
   typedef struct TYPE_NAME TYPE_NAME;                                                 \
   struct TYPE_NAME {                                                                  \
      bool ok;                                                                         \
      MEMBERS                                                                          \
   };

#define ASSERT(expr)                                                                   \
   if (!(expr)) {                                                                      \
      PANIC("Assertion Failed %s in file %s:%d\n", #expr, __FILE__, __LINE__);         \
   }

typedef size_t usize;

static const usize USIZE_MAX = SIZE_MAX;

enum Type {
   TypeBool,
   TypeInt,
   TypeFloat,
   TypeStr,
   TypeTuple,
   TypeList,
};

enum NodeType {
   NodeTypeLeaf,
   NodeTypeBranch,
};

enum TokenType {
   TokenTypeNull,
   TokenTypeBool,
   TokenTypeInt,
   TokenTypeFloat,
   TokenTypeStr,
   TokenTypeIdentifier,
   TokenTypeKeyword,
};

enum Keyword {
   KeywordDefun,
   KeywordSet,
   KeywordIf,
   KeywordElse,
   KeywordWhile,
   KeywordPrint,
   KeywordAdd,
   KeywordSub,
   KeywordMul,
   KeywordDiv,
   KeywordMod,
   KeywordEq,
   KeywordLt,
   KeywordGt,
   KeywordNot,
   KeywordAnd,
   KeywordOr,
   KeywordList,
   KeywordGetItem,
   KeywordLen,
   KeywordSetItem,
   KeywordIndex,
   KeywordPush,
   KeywordRemove,
   KeywordBool,
   KeywordInt,
   KeywordFloat,
   KeywordStr,
   KeywordReturn,
   KeywordFor,
   KeywordType,
   KeywordTernary,
};

typedef enum Type Type;
typedef enum NodeType NodeType;
typedef enum TokenType TokenType;
typedef enum Keyword Keyword;
typedef struct Return Return;
typedef struct Slice Slice;
typedef struct Tuple Tuple;
typedef struct Value Value;
typedef struct Node Node;
typedef struct Lexer Lexer;
typedef struct State State;

DEFINE_RESULT_TYPE(ParseIntResult, int value;)
DEFINE_RESULT_TYPE(ParseFloatResult, double value;)
DEFINE_RESULT_TYPE(GetKeywordResult, Keyword value;)

struct Return {
   bool returned;
   Value * value;
};

struct Slice {
   char * str;
   usize len;
};

DEFINE_VEC(ValuePtrVec, Value *)
DEFINE_VEC(CharVec, char)
DEFINE_VEC(NodePtrVec, Node *)
DEFINE_VEC(SliceVec, Slice)

struct Tuple {
   Value ** data;
   usize len;
};

struct Value {
   Type type;
   usize references;

   union {
      bool _bool;
      int _int;
      double _float;
      char * _str;
      Tuple _tuple;
      ValuePtrVec _list;
   };
};

struct Node {
   NodeType type;
   /* id is used to store indices for functions, variables and keywords.
    * If node is a variable identifier, id is the offset from the beginning of
    * the stack for that variable. If node is a function identifier, id is an
    * index for `state.functions` */
   usize id;

   union {
      struct {
         TokenType token_type;
         Slice token;

         union {
            bool _bool;
            int _int;
            double _float;
            Keyword _keyword;
         };
      };

      NodePtrVec children;
   };
};

struct Lexer {
   char * source;
   usize i;
};

static const Slice LexerEOF = (Slice){.str = NULL, .len = 0};

struct State {
   CharVec source;
   Node * root;
   SliceVec function_names;
   NodePtrVec functions;
   ValuePtrVec variables;
   usize variables_begin;
};

GetKeywordResult get_keyword(Slice token);
ParseIntResult parse_int(Slice slice);
ParseFloatResult parse_float(Slice slice);
bool char_in_str(char c, char * str);
bool slice_eq_str(Slice slice, char * str);
bool slice_eq(Slice left, Slice right);
bool slice_is(Slice left, Slice right);
Slice str_as_slice(char * str);
Node * node_new_leaf(Slice token);
Node * node_new_branch(void);
void node_fprint(Node * node, FILE * file);
void D_node_fprint(Node * node, FILE * file, usize indent);
void node_free(Node * node);
Value * value_new_bool(bool _bool);
Value * value_new_int(int _int);
Value * value_new_float(double _float);
Value * value_new_str(const char * _str);
Value * value_new_str_concat(char * left, char * right);
Value * value_new_str_from_slice(Slice * slice);
Value * value_new_str_from_len(usize len);
Value * value_new_str_from_literal(Slice * slice);
Value * value_new_list(void);
void value_free(Value * value);
Value * value_ref(Value * value);
void value_drop(Value * value);
bool value_as_bool(Value * value);
int int_mod(int left, int right);
double float_mod(double left, double right);
Value * value_mod(Value * left, Value * right);
void value_fprint(Value * value, FILE * file);
CharVec file_read(FILE * file);
Lexer lexer_new(char * source);
bool lexer_whitespace(Lexer * lexer);
bool lexer_comment(Lexer * lexer);
bool lexer_ignore(Lexer * lexer);
Slice lexer_next(Lexer * lexer);
Node * parse(Lexer * lexer);
void functions(State * state);
void variables(State * state, Node * node, SliceVec * variable_names);
State state_new(FILE * file);
void state_free(State * state);
void compile(State * state);
Value * builtin_set(State * state, Node * node);
void builtin_print(State * state, Node * node);
void builtin_setitem(State * state, Node * node);
void builtin_push(State * state, Node * node);
void builtin_remove(State * state, Node * node);
Value * builtin_add(State * state, Node * node);
Value * builtin_sub(State * state, Node * node);
Value * builtin_mul(State * state, Node * node);
Value * builtin_div(State * state, Node * node);
Value * builtin_mod(State * state, Node * node);
Value * builtin_eq(State * state, Node * node);
Value * builtin_lt(State * state, Node * node);
Value * builtin_gt(State * state, Node * node);
Value * builtin_not(State * state, Node * node);
Value * builtin_and(State * state, Node * node);
Value * builtin_or(State * state, Node * node);
Value * builtin_list(State * state, Node * node);
Value * builtin_getitem(State * state, Node * node);
Value * builtin_len(State * state, Node * node);
Value * builtin_index(State * state, Node * node);
Value * builtin_bool(State * state, Node * node);
Value * builtin_int(State * state, Node * node);
Value * builtin_float(State * state, Node * node);
Value * builtin_str(State * state, Node * node);
Value * builtin_type(State * state, Node * node);
Value * builtin_ternary(State * state, Node * node);
Value * eval(State * state, Node * node);
Return exec(State * state, Node * node);
Value * get_variable(State * state, usize id);
void set_variable(State * state, usize id, Value * value);
Return exec_all(State * state, Node * node);
Return call(State * state, usize function_id);
void run(State * state);
void test(void);
