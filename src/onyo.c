#include "onyo.h"

#include <math.h>
#include <string.h>

/* sexpr - A dynamic interpreted programming language. *
 * ----------------------------------------------------------------------------------
 * * This uses reference counting to automatically manage memory. The syntax is
 * * LISP-like, which means it uses S-expressions. This was choosen because *
 * S-expressions are notoriously easy to parse. */

#define LEXER_FOR_EACH(LEXER, VARIABLE)                                                \
   for (Slice VARIABLE = lexer_next(LEXER); !slice_is(VARIABLE, LexerEOF);             \
        VARIABLE = lexer_next(LEXER))

#define BRANCH(VAR, NODE)                                                              \
   Node * VAR = NODE;                                                                  \
   if (VAR->type != NodeTypeBranch)

#define CONST(VAR, NODE, TOKEN)                                                        \
   Node * VAR = NODE;                                                                  \
   if (VAR->type != NodeTypeLeaf || !slice_eq_str(VAR->token, TOKEN))

#define LEAF(VAR, NODE)                                                                \
   Node * VAR = NODE;                                                                  \
   if (VAR->type != NodeTypeLeaf)

#define STREQ(left, right) 0 == strcmp(left, right)

/* This could have been called List but it is also used in other places. */
IMPL_VEC(ValuePtrVec, Value *, DEFAULT_EQUALS)
/* CharVec.len will report the length of the contents + 1. */
IMPL_VEC(CharVec, char, DEFAULT_EQUALS)
IMPL_VEC(CharPtrVec, char *, STREQ)
IMPL_VEC(NodePtrVec, Node *, DEFAULT_EQUALS)
IMPL_VEC(SliceVec, Slice, slice_eq)

Value * table_get(Table * table, char * key) {
   usize index = CharPtrVec_index(&table->keys, key);
   if (index == table->keys.len) {
      return NULL;
   }
   return value_ref(table->values.data[index]);
}

void table_set(Table * table, char * key, Value * value) {
   usize index = CharPtrVec_index(&table->keys, key);
   if (index != table->keys.len) {
      value_drop(table->values.data[index]);
      table->values.data[index] = value;
   } else {
      char * keyclone = malloc(sizeof(char) * (strlen(key) + 1));
      strcpy(keyclone, key);
      CharPtrVec_push(&table->keys, keyclone);
      ValuePtrVec_push(&table->values, value);
   }
}

void table_remove(Table * table, char * key) {
   usize index = CharPtrVec_index(&table->keys, key);
   if (index != table->keys.len) {
      free(table->keys.data[index]);
      value_drop(table->values.data[index]);
      CharPtrVec_remove(&table->keys, index);
      ValuePtrVec_remove(&table->values, index);
   }
}

void table_free(Table * table) {
   for (usize i = 0; i < table->keys.len; i++) {
      free(table->keys.data[i]);
   }
   for (usize i = 0; i < table->values.len; i++) {
      value_drop(table->values.data[i]);
   }
   CharPtrVec_free(&table->keys);
   ValuePtrVec_free(&table->values);
}

#define KEYWORD(STR, VAL)                                                              \
   if (slice_eq_str(token, STR)) {                                                     \
      return (GetKeywordResult){true, VAL};                                            \
   }

GetKeywordResult get_keyword(Slice token) {
   KEYWORD("defun", KeywordDefun)
   KEYWORD("set", KeywordSet)
   KEYWORD("if", KeywordIf)
   KEYWORD("else", KeywordElse)
   KEYWORD("while", KeywordWhile)
   KEYWORD("print", KeywordPrint)
   KEYWORD("+", KeywordAdd)
   KEYWORD("-", KeywordSub)
   KEYWORD("*", KeywordMul)
   KEYWORD("/", KeywordDiv)
   KEYWORD("%", KeywordMod)
   KEYWORD("=", KeywordEq)
   KEYWORD("<", KeywordLt)
   KEYWORD(">", KeywordGt)
   KEYWORD("!", KeywordNot)
   KEYWORD("&", KeywordAnd)
   KEYWORD("|", KeywordOr)
   KEYWORD("list", KeywordList)
   KEYWORD("table", KeywordTable)
   KEYWORD("item", KeywordGetItem)
   KEYWORD("len", KeywordLen)
   KEYWORD("setitem", KeywordSetItem)
   KEYWORD("index", KeywordIndex)
   KEYWORD("push", KeywordPush)
   KEYWORD("remove", KeywordRemove)
   KEYWORD("bool", KeywordBool)
   KEYWORD("int", KeywordInt)
   KEYWORD("float", KeywordFloat)
   KEYWORD("str", KeywordStr)
   KEYWORD("return", KeywordReturn)
   KEYWORD("for", KeywordFor)
   KEYWORD("type", KeywordType)
   KEYWORD("ternary", KeywordTernary)
   return (GetKeywordResult){.ok = false};
}

#undef KEYWORD

ParseIntResult parse_int(Slice slice) {
   ParseIntResult result = {true, 0};
   char * endptr;
   result.value = (int)strtol(slice.str, &endptr, 0);
   if (slice.str == endptr || (usize)(endptr - slice.str) != slice.len) {
      result.ok = false;
   }
   return result;
}

ParseFloatResult parse_float(Slice slice) {
   char * endptr;
   double value = strtod(slice.str, &endptr);
   if (slice.str == endptr || (usize)(endptr - slice.str) != slice.len) {
      return (ParseFloatResult){false};
   }
   return (ParseFloatResult){true, value};
}

/* Returns true if char is any of str. Cannot be used to test if c is '\0'. */
bool char_in_str(char c, char * str) {
   while (*str != c) {
      if (!*str) {
         return false;
      }
      str++;
   }
   return true;
}

/* Returns true if slice is equal to str. */
bool slice_eq_str(Slice slice, char * str) {
   usize i = 0;
   for (i = 0; i < slice.len; i++) {
      if (str[i] == '\0' || slice.str[i] != str[i]) {
         return false;
      }
   }
   return str[i] == '\0';
}

/* Returns true if both slices are equal. */
bool slice_eq(Slice left, Slice right) {
   if (left.len != right.len) {
      return false;
   }
   for (usize i = 0; i < left.len; i++) {
      if (left.str[i] != right.str[i]) {
         return false;
      }
   }
   return true;
}

/* Returns true if both slices point to same data. */
bool slice_is(Slice left, Slice right) {
   return left.str == right.str && left.len == right.len;
}

/* The returned slice does not own the data. */
Slice str_as_slice(char * str) {
   return (Slice){.str = str, .len = strlen(str)};
}

Node * node_new_leaf(Slice token) {
   Node * node = malloc(sizeof(Node));
   node->type = NodeTypeLeaf;
   node->id = USIZE_MAX;
   node->token = token;
   node->token_type = TokenTypeIdentifier;
   if (token.str[0] == '"') {
      node->token_type = TokenTypeStr;
   } else if (slice_eq_str(token, "true")) {
      node->token_type = TokenTypeBool;
      node->_bool = true;
   } else if (slice_eq_str(token, "false")) {
      node->token_type = TokenTypeBool;
      node->_bool = false;
   } else if (slice_eq_str(token, "null")) {
      node->token_type = TokenTypeNull;
   } else {
      ParseIntResult result = parse_int(token);
      if (result.ok) {
         node->token_type = TokenTypeInt;
         node->_int = result.value;
      } else {
         ParseFloatResult result = parse_float(token);
         if (result.ok) {
            node->token_type = TokenTypeFloat;
            node->_float = result.value;
         } else {
            GetKeywordResult result = get_keyword(token);
            if (result.ok) {
               node->token_type = TokenTypeKeyword;
               node->_keyword = result.value;
            }
         }
      }
   }
   return node;
}

Node * node_new_branch(void) {
   Node * node = malloc(sizeof(Node));
   node->type = NodeTypeBranch;
   node->id = USIZE_MAX;
   node->children = NodePtrVec_new();
   return node;
}

void node_fprint(Node * node, FILE * file) {
   D_node_fprint(node, file, 0);
}

void D_node_fprint(Node * node, FILE * file, usize indent) {
   switch (node->type) {
   case NodeTypeLeaf:
      if (node->id == USIZE_MAX) {
         fprintf(file, "Lead(token='%.*s')", (int)node->token.len, node->token.str);
      } else {
         fprintf(
             file,
             "Lead(token='%.*s', id=%lu)",
             (int)node->token.len,
             node->token.str,
             node->id
         );
      }
      break;
   case NodeTypeBranch:
      fprintf(file, "Branch(");
      if (node->id != USIZE_MAX) {
         fprintf(file, "id=%lu, ", node->id);
      }
      fprintf(file, "children=[");
      for (usize i = 0; i < node->children.len; i++) {
         D_node_fprint(node->children.data[i], file, indent + 1);
         if (i != node->children.len - 1) {
            fprintf(file, ", ");
         }
      }
      fprintf(file, "])");
      break;
   }
}

void node_free(Node * node) {
   switch (node->type) {
   case NodeTypeLeaf:
      break;
   case NodeTypeBranch:
      for (usize i = 0; i < node->children.len; i++) {
         node_free(node->children.data[i]);
      }
      NodePtrVec_free(&node->children);
      break;
   }
   free(node);
}

static Value TRUE = {.type = TypeBool, .references = 0, ._bool = true};
static Value FALSE = {.type = TypeBool, .references = 0, ._bool = false};

Value * value_new_bool(bool _bool) {
   if (_bool) {
      TRUE.references++;
      return &TRUE;
   } else {
      FALSE.references++;
      return &FALSE;
   }
}

Value * value_new_int(int _int) {
   Value * value = malloc(sizeof(Value));
   value->references = 1;
   value->type = TypeInt;
   value->_int = _int;
   return value;
}

Value * value_new_float(double _float) {
   Value * value = malloc(sizeof(Value));
   value->references = 1;
   value->type = TypeFloat;
   value->_float = _float;
   return value;
}

Value * value_new_str(const char * _str) {
   Value * value = malloc(sizeof(Value));
   value->references = 1;
   value->type = TypeStr;
   usize len = strlen(_str) + 1;
   value->_str = malloc(sizeof(char) * len);
   strcpy(value->_str, _str);
   return value;
}

Value * value_new_str_concat(char * left, char * right) {
   Value * value = malloc(sizeof(Value));
   value->references = 1;
   value->type = TypeStr;
   usize left_len = strlen(left);
   value->_str = malloc(left_len + strlen(right) + 1);
   strcpy(value->_str, left);
   strcpy(value->_str + left_len, right);
   return value;
}

/* If slice is a str literal, use `value_new_str_from_literal()` instead. */
Value * value_new_str_from_slice(Slice * slice) {
   Value * value = malloc(sizeof(Value));
   value->references = 1;
   value->type = TypeStr;
   value->_str = malloc(sizeof(char) * slice->len + 1);
   memcpy(value->_str, slice->str, sizeof(char) * slice->len);
   value->_str[slice->len] = '\0';
   return value;
}

Value * value_new_str_from_len(usize len) {
   Value * value = malloc(sizeof(Value));
   value->references = 1;
   value->type = TypeStr;
   value->_str = malloc(sizeof(char) * len + 1);
   value->_str[len] = '\0';
   return value;
}

/* Parses a str literal. */
Value * value_new_str_from_literal(Slice * slice) {
   if (slice->len < 2 || slice->str[0] != '"' || slice->str[slice->len - 1] != '"') {
      PANIC("Failed to parse str literal. %.*s\n", (int)slice->len, slice->str);
   }
   Value * value = malloc(sizeof(Value));
   value->references = 1;
   value->type = TypeStr;
   /* Would allocate more than required but doesn't matter. */
   value->_str = malloc(sizeof(char) * slice->len);
   usize j = 0;
   for (usize i = 1; i < slice->len - 1; i++) {
      if (slice->str[i] == '\\') {
         i++;
         if (i + 1 == slice->len) {
            PANIC("Unescaped backslash. %.*s\n", (int)slice->len, slice->str);
         }
         switch (slice->str[i]) {
         case 'n':
            value->_str[j] = '\n';
            j++;
            continue;
         case 't':
            value->_str[j] = '\t';
            j++;
            continue;
         }
      }
      value->_str[j] = slice->str[i];
      j++;
   }
   value->_str[j] = '\0';
   return value;
}

Value * value_new_list(void) {
   Value * value = malloc(sizeof(Value));
   value->references = 1;
   value->type = TypeList;
   value->_list = ValuePtrVec_new();
   return value;
}

Value * value_new_table(void) {
   Value * value = malloc(sizeof(Value));
   value->references = 1;
   value->type = TypeTable;
   value->_table.keys = CharPtrVec_new();
   value->_table.values = ValuePtrVec_new();
   return value;
}

/* Recursively frees value, in future should defer freeing */
void value_free(Value * value) {
   if (value == NULL || value == &TRUE || value == &FALSE) {
      return;
   }
   switch (value->type) {
   case TypeStr:
      if (value->_str != NULL) {
         free(value->_str);
      }
      break;
   case TypeTuple:
      if (value->_tuple.data != NULL) {
         free(value->_tuple.data);
      }
      break;
   case TypeList:
      for (usize i = 0; i < value->_list.len; i++) {
         value_drop(value->_list.data[i]);
      }
      ValuePtrVec_free(&value->_list);
      break;
   case TypeTable:
      table_free(&value->_table);
      break;
   default:
      break;
   }
   free(value);
}

/* Must be called before storing a reference to a value. */
Value * value_ref(Value * value) {
   if (value != NULL) {
      value->references++;
   }
   return value;
}

/* Must be called when dropping a reference to a value. Must not use reference
 * after dropping */
void value_drop(Value * value) {
   if (value == NULL) {
      return;
   }
   if (value->references <= 1) {
      value_free(value);
      return;
   }
   value->references -= 1;
}

/* Coerce value to bool */
bool value_as_bool(Value * value) {
   if (value == NULL) {
      return false;
   }
   if (value == &TRUE) {
      return true;
   }
   if (value == &FALSE) {
      return false;
   }
   switch (value->type) {
   case TypeBool:
      return value->_bool;
   case TypeInt:
      return (bool)value->_int;
   case TypeFloat:
      return (bool)value->_float;
   case TypeStr:
      return strlen(value->_str) != 0;
   case TypeTuple:
      return value->_tuple.len != 0;
   case TypeList:
      return value->_list.len != 0;
   case TypeTable:
      return value->_table.values.len != 0;
   }
}

int int_mod(int left, int right) {
   int mod = left % right;
   if (right < 0 != mod < 0) {
      mod += right;
   }
   return mod;
}

double float_mod(double left, double right) {
   double mod = fmod(left, right);
   if (right < 0 != mod < 0) {
      mod += right;
   }
   return mod;
}

Value * value_mod(Value * left, Value * right) {
   if (left == NULL || right == NULL) {
      return NULL;
   }
   Value * result = NULL;
   switch (left->type) {
   case TypeInt:
      switch (right->type) {
      case TypeInt:
         result = value_new_int(int_mod(left->_int, right->_int));
         break;
      case TypeFloat:
         result = value_new_float(float_mod((double)left->_int, right->_float));
         break;
      default:
         break;
      }
      break;
   case TypeFloat:
      switch (right->type) {
      case TypeInt:
         result = value_new_float(float_mod(left->_float, (double)right->_int));
         break;
      case TypeFloat:
         result = value_new_float(float_mod(left->_float, right->_float));
         break;
      default:
         break;
      }
      break;
   default:
      break;
   }
   return result;
}

void value_fprint(Value * value, FILE * file) {
   if (value == NULL) {
      fputs("null", file);
      return;
   }
   switch (value->type) {
   case TypeBool:
      if (value->_bool) {
         fputs("true", file);
      } else {
         fputs("false", file);
      }
      break;
   case TypeInt:
      fprintf(file, "%d", value->_int);
      break;
   case TypeFloat:
      fprintf(file, "%g", (double)value->_float);
      break;
   case TypeStr: {
      char * ptr = value->_str;
      fputs("\"", file);
      while (*ptr) {
         switch (*ptr) {
         case '\n':
            fputs("\\n", file);
            break;
         case '\t':
            fputs("\\t", file);
            break;
         case '\\':
            fputs("\\\\", file);
            break;
         case '"':
            fputs("\\\\", file);
            break;
         default:
            fputc(*ptr, file);
         }
         ptr++;
      }
      fputs("\"", file);
      break;
   }
   case TypeTuple:
      fputs("(tuple", file);
      for (usize i = 0; i < value->_tuple.len; i++) {
         fputs(" ", file);
         value_fprint(value->_tuple.data[i], file);
      }
      fputs(")", file);
      break;
   case TypeList:
      fputs("(list", file);
      for (usize i = 0; i < value->_list.len; i++) {
         fputs(" ", file);
         value_fprint(value->_list.data[i], file);
      }
      fputs(")", file);
      break;
   case TypeTable:
      fputs("{", file);
      for (usize i = 0; i < value->_table.values.len; i++) {
         fprintf(file, "%s: ", value->_table.keys.data[i]);
         value_fprint(value->_table.values.data[i], file);
         fputs(", ", file);
      }
      fputs("}", file);
   }
}

/* .len is 1 + the length of the string content. */
CharVec file_read(FILE * file) {
   CharVec buf = CharVec_new();
   while (true) {
      int c = fgetc(file);
      if (c == EOF) {
         CharVec_push(&buf, '\0');
         break;
      }
      CharVec_push(&buf, (char)c);
   }
   return buf;
}

Lexer lexer_new(char * source) {
   return (Lexer){.source = source, .i = 0};
}

bool lexer_whitespace(Lexer * lexer) {
   bool done = false;
   while (lexer->source[lexer->i] != '\0'
          && char_in_str(lexer->source[lexer->i], " \n\t")) {
      lexer->i++;
      done = true;
   }
   return done;
}

bool lexer_comment(Lexer * lexer) {
   if (lexer->source[lexer->i] == ';') {
      while (lexer->source[lexer->i] != '\0' && lexer->source[lexer->i] != '\n') {
         lexer->i++;
      }
      if (lexer->source[lexer->i] == '\n') {
         lexer->i++;
      }
      return true;
   }
   return false;
}

bool lexer_ignore(Lexer * lexer) {
   bool done = false;
   while (lexer_whitespace(lexer)) {
      done = true;
   }
   while (lexer_comment(lexer)) {
      done = true;
   }
   return done;
}

Slice lexer_next(Lexer * lexer) {
   while (lexer_ignore(lexer)) {}
   if (lexer->source[lexer->i] == '\0') {
      return LexerEOF;
   }
   if (lexer->source[lexer->i] == '"') {
      usize begin = lexer->i;
      lexer->i++;
      while (lexer->source[lexer->i] != '"') {
         if (lexer->source[lexer->i] == '\0') {
            return LexerEOF;
         }
         if (lexer->source[lexer->i] == '\\') {
            lexer->i++;
            if (lexer->source[lexer->i] == '\0') {
               return LexerEOF;
            }
         }
         lexer->i++;
      }
      lexer->i++;
      return (Slice){.str = lexer->source + begin, lexer->i - begin};
   }
   if (char_in_str(lexer->source[lexer->i], "()")) {
      lexer->i++;
      return (Slice){.str = lexer->source + lexer->i - 1, .len = 1};
   }
   usize begin = lexer->i;
   while (lexer->source[lexer->i] != '\0'
          && !char_in_str(lexer->source[lexer->i], " \n\t\";()")) {
      lexer->i++;
   }
   return (Slice){.str = lexer->source + begin, lexer->i - begin};
}

Node * parse(Lexer * lexer) {
   NodePtrVec stack = NodePtrVec_new();
   Node * root = node_new_branch();
   Node * node = root;
   LEXER_FOR_EACH(lexer, token) {
      if (slice_eq_str(token, "(")) {
         Node * sub_node = node_new_branch();
         NodePtrVec_push(&node->children, sub_node);
         NodePtrVec_push(&stack, node);
         node = sub_node;
      } else if (slice_eq_str(token, ")")) {
         node = stack.data[stack.len - 1];
         NodePtrVec_remove(&stack, stack.len - 1);
      } else {
         Node * sub_node = node_new_leaf(token);
         NodePtrVec_push(&node->children, sub_node);
      }
   }
   NodePtrVec_free(&stack);
   return root;
}

void functions(State * state) {
   SliceVec_push(&state->function_names, (Slice){.str = NULL, .len = 0});
   NodePtrVec_push(&state->functions, NULL);
   for (usize i = 0; i < state->root->children.len; i++) {
      BRANCH(defun, state->root CHILD(i)) {
         continue;
      }
      CONST(tag, defun CHILD(0), "defun") {
         continue;
      }
      BRANCH(prototype, defun CHILD(1)) {
         PANIC("Expected prototype.\n");
      }
      LEAF(name, prototype CHILD(0)) {
         PANIC("Expected identifier.\n");
      }
      if (slice_eq_str(name->token, "main")) {
         if (state->functions.data[0] != NULL) {
            PANIC("Redeclaration of main function.\n");
         }
         state->function_names.data[0] = name->token;
         state->functions.data[0] = defun;
         prototype->id = 0;
         continue;
      }
      if (SliceVec_index(&state->function_names, name->token)
          != state->function_names.len) {
         PANIC(
             "Redeclaration of function with name %.*s.\n",
             (int)name->token.len,
             name->token.str
         );
      }
      prototype->id = state->functions.len;
      SliceVec_push(&state->function_names, name->token);
      NodePtrVec_push(&state->functions, defun);
   }
   if (state->functions.data[0] == NULL) {
      PANIC("No main function declared.\n");
   }
   SliceVec variable_names = SliceVec_new();
   for (usize i = 0; i < state->functions.len; i++) {
      Node * defun = state->functions.data[i];
      SliceVec_clear(&variable_names);
      variables(state, defun, &variable_names);
      defun->id = variable_names.len;
   }
   SliceVec_free(&variable_names);
}

void variables(State * state, Node * node, SliceVec * variable_names) {
   switch (node->type) {
   case NodeTypeLeaf: {
      if (node->token_type != TokenTypeIdentifier) {
         return;
      }
      usize index = SliceVec_index(&state->function_names, node->token);
      if (index != state->function_names.len) {
         node->id = index;
         return;
      }
      index = SliceVec_index(variable_names, node->token);
      if (index == variable_names->len) {
         SliceVec_push(variable_names, node->token);
      }
      node->id = index;
      break;
   }
   case NodeTypeBranch:
      for (usize i = 0; i < node->children.len; i++) {
         variables(state, node CHILD(i), variable_names);
      }
      break;
   }
}

State state_new(FILE * file) {
   CharVec source = file_read(file);
   Lexer lexer = lexer_new(source.data);
   return (State
   ){.source = source,
     .root = parse(&lexer),
     .function_names = SliceVec_new(),
     .functions = NodePtrVec_new(),
     .variables = ValuePtrVec_new(),
     .variables_begin = 0};
}

void state_free(State * state) {
   ValuePtrVec_free(&state->variables);
   NodePtrVec_free(&state->functions);
   SliceVec_free(&state->function_names);
   node_free(state->root);
   CharVec_free(&state->source);
}

void compile(State * state) {
   functions(state);
}

Value * builtin_set(State * state, Node * node) {
   LEAF(variable, node CHILD(1)) {
      PANIC("Expected variable.\n");
   }
   Node * expr = node CHILD(2);
   Value * value = eval(state, expr);
   set_variable(state, variable->id, value);
   return value_ref(value);
}

void builtin_print(State * state, Node * node) {
   Node * expr = node CHILD(1);
   Value * value = eval(state, expr);
   if (value != NULL && value->type == TypeStr) {
      printf("%s", value->_str);
   } else {
      value_fprint(value, stdout);
      fprintf(stdout, "\n");
   }
   value_drop(value);
}

void builtin_setitem(State * state, Node * node) {
   Value * list = eval(state, node CHILD(1));
   Value * index = eval(state, node CHILD(2));
   Value * item = eval(state, node CHILD(3));

   if (list == NULL || index == NULL) {
      value_drop(list);
      value_drop(index);
      value_drop(item);
      return;
   }

   switch (index->type) {
   case TypeInt:
      switch (list->type) {
      case TypeList:
         if (0 <= index->_int && index->_int < (int)list->_list.len) {
            value_drop(list->_list.data[index->_int]);
            list->_list.data[index->_int] = item;
            value_drop(list);
            value_drop(index);
            return;
         }
         break;
      default:
         break;
      }
      break;
   case TypeStr:
      switch (list->type) {
      case TypeTable: {
         table_set(&list->_table, index->_str, item);
         value_drop(list);
         value_drop(index);
         return;
      }
      default:
         break;
      }
      break;
   default:
      break;
   }

   value_drop(index);
   value_drop(list);
   value_drop(item);
}

void builtin_push(State * state, Node * node) {
   Value * list = eval(state, node CHILD(1));
   Value * item = eval(state, node CHILD(2));
   if (list->type == TypeList) {
      ValuePtrVec_push(&list->_list, item);
   }
   value_drop(list);
}

void builtin_remove(State * state, Node * node) {
   Value * list = eval(state, node CHILD(1));
   Value * index = eval(state, node CHILD(2));
   if (list->type == TypeList) {
      if (index->type == TypeInt) {
         if (0 <= index->_int && index->_int < (int)list->_list.len) {
            value_drop(list->_list.data[index->_int]);
            ValuePtrVec_remove(&list->_list, (usize)index->_int);
         }
      }
   }
   value_drop(index);
   value_drop(list);
}

Value * builtin_add(State * state, Node * node) {
   if (node->children.len != 3) {
      PANIC("Call error.\n");
   }
   Node * left = node CHILD(1);
   Node * right = node CHILD(2);
   Value * left_val = eval(state, left);
   Value * right_val = eval(state, right);
   Value * result = NULL;
   if (left_val != NULL && right_val != NULL) {
      switch (left_val->type) {
      case TypeInt:
         switch (right_val->type) {
         case TypeInt:
            result = value_new_int(left_val->_int + right_val->_int);
            break;
         case TypeFloat:
            result = value_new_float((double)left_val->_int + right_val->_float);
            break;
         default:
            break;
         }
         break;
      case TypeFloat:
         switch (right_val->type) {
         case TypeInt:
            result = value_new_float(left_val->_float + (double)right_val->_int);
            break;
         case TypeFloat:
            result = value_new_float((double)left_val->_float + right_val->_float);
            break;
         default:
            break;
         }
         break;
      case TypeStr:
         switch (right_val->type) {
         case TypeStr:
            result = value_new_str_concat(left_val->_str, right_val->_str);
            break;
         default:
            break;
         }
         break;
      default:
         break;
      }
   }
   value_drop(left_val);
   value_drop(right_val);
   return result;
}

Value * builtin_sub(State * state, Node * node) {
   if (node->children.len < 2) {
      PANIC("Call error.\n");
   } else if (node->children.len == 2) {
      Node * expr = node CHILD(1);
      Value * value = eval(state, expr);
      Value * result = NULL;
      if (value != NULL) {
         switch (value->type) {
         case TypeInt:
            result = value_new_int(0 - value->_int);
            break;
         case TypeFloat:
            result = value_new_float(0 - value->_float);
            break;
         default:
            break;
         }
      }
      value_drop(value);
      return result;
   }
   Node * left = node CHILD(1);
   Node * right = node CHILD(2);
   Value * left_val = eval(state, left);
   Value * right_val = eval(state, right);
   Value * result = NULL;
   if (left_val != NULL && right_val != NULL) {
      switch (left_val->type) {
      case TypeInt:
         switch (right_val->type) {
         case TypeInt:
            result = value_new_int(left_val->_int - right_val->_int);
            break;
         case TypeFloat:
            result = value_new_float((double)left_val->_int - right_val->_float);
            break;
         default:
            break;
         }
         break;
      case TypeFloat:
         switch (right_val->type) {
         case TypeInt:
            result = value_new_float(left_val->_float - (double)right_val->_int);
            break;
         case TypeFloat:
            result = value_new_float(left_val->_float - right_val->_float);
            break;
         default:
            break;
         }
         break;
      default:
         break;
      }
   }
   value_drop(left_val);
   value_drop(right_val);
   return result;
}

Value * builtin_mul(State * state, Node * node) {
   if (node->children.len != 3) {
      PANIC("Call error.\n");
   }
   Node * left = node CHILD(1);
   Node * right = node CHILD(2);
   Value * left_val = eval(state, left);
   Value * right_val = eval(state, right);
   Value * result = NULL;
   if (left_val != NULL && right_val != NULL) {
      switch (left_val->type) {
      case TypeInt:
         switch (right_val->type) {
         case TypeInt:
            result = value_new_int(left_val->_int * right_val->_int);
            break;
         case TypeFloat:
            result = value_new_float((double)left_val->_int * right_val->_float);
            break;
         default:
            break;
         }
         break;
      case TypeFloat:
         switch (right_val->type) {
         case TypeInt:
            result = value_new_float(left_val->_float * (double)right_val->_int);
            break;
         case TypeFloat:
            result = value_new_float((double)left_val->_float * right_val->_float);
            break;
         default:
            break;
         }
         break;
      default:
         break;
      }
   }
   value_drop(left_val);
   value_drop(right_val);
   return result;
}

Value * builtin_div(State * state, Node * node) {
   if (node->children.len != 3) {
      PANIC("Call error.\n");
   }
   Node * left = node CHILD(1);
   Node * right = node CHILD(2);
   Value * left_val = eval(state, left);
   Value * right_val = eval(state, right);
   Value * result = NULL;
   if (left_val != NULL && right_val != NULL) {
      switch (left_val->type) {
      case TypeInt:
         switch (right_val->type) {
         case TypeInt:
            result = value_new_int(left_val->_int / right_val->_int);
            break;
         case TypeFloat:
            result = value_new_float((double)left_val->_int / right_val->_float);
            break;
         default:
            break;
         }
         break;
      case TypeFloat:
         switch (right_val->type) {
         case TypeInt:
            result = value_new_float(left_val->_float / (double)right_val->_int);
            break;
         case TypeFloat:
            result = value_new_float((double)left_val->_float / right_val->_float);
            break;
         default:
            break;
         }
         break;
      default:
         break;
      }
   }
   value_drop(left_val);
   value_drop(right_val);
   return result;
}

Value * builtin_mod(State * state, Node * node) {
   Value * left = eval(state, node CHILD(1));
   Value * right = eval(state, node CHILD(2));
   Value * result = value_mod(left, right);
   value_drop(left);
   value_drop(right);
   return result;
}

Value * builtin_eq(State * state, Node * node) {
   if (node->children.len != 3) {
      PANIC("Call error.\n");
   }
   Node * left = node CHILD(1);
   Node * right = node CHILD(2);
   Value * left_val = eval(state, left);
   Value * right_val = eval(state, right);
   Value * result = NULL;
   if (left_val != NULL && right_val != NULL) {
      switch (left_val->type) {
      case TypeBool:
         switch (right_val->type) {
         case TypeBool:
            result = value_new_bool(left_val->_bool == right_val->_bool);
            break;
         default:
            break;
         }
         break;
      case TypeInt:
         switch (right_val->type) {
         case TypeInt:
            result = value_new_bool(left_val->_int == right_val->_int);
            break;
         default:
            break;
         }
         break;
      case TypeFloat:
         switch (right_val->type) {
         case TypeFloat:
            result = value_new_bool(left_val->_float == right_val->_float);
            break;
         default:
            break;
         }
         break;
      case TypeStr:
         switch (right_val->type) {
         case TypeStr:
            result = value_new_bool(0 == strcmp(left_val->_str, right_val->_str));
            break;
         default:
            break;
         }
         break;
      case TypeTuple:
         switch (right_val->type) {
         case TypeTuple:
            // TODO
            break;
         default:
            break;
         }
         break;
      default:
         break;
      }
   }
   if (result == NULL) {
      result = value_new_bool(false);
   }
   value_drop(left_val);
   value_drop(right_val);
   return result;
}

Value * builtin_lt(State * state, Node * node) {
   if (node->children.len != 3) {
      PANIC("Call error.\n");
   }
   Node * left = node CHILD(1);
   Node * right = node CHILD(2);
   Value * left_val = eval(state, left);
   Value * right_val = eval(state, right);
   Value * result = NULL;
   if (left_val != NULL && right_val != NULL) {
      switch (left_val->type) {
      case TypeBool:
         switch (right_val->type) {
         case TypeBool:
            result = value_new_bool(left_val->_bool < right_val->_bool);
            break;
         case TypeInt:
            result = value_new_bool(left_val->_bool < right_val->_int);
            break;
         case TypeFloat:
            result = value_new_bool(left_val->_bool < right_val->_float);
            break;
         default:
            break;
         }
         break;
      case TypeInt:
         switch (right_val->type) {
         case TypeBool:
            result = value_new_bool(left_val->_int < right_val->_bool);
            break;
         case TypeInt:
            result = value_new_bool(left_val->_int < right_val->_int);
            break;
         case TypeFloat:
            result = value_new_bool(left_val->_int < right_val->_float);
            break;
         default:
            break;
         }
         break;
      case TypeFloat:
         switch (right_val->type) {
         case TypeBool:
            result = value_new_bool(left_val->_float < right_val->_bool);
            break;
         case TypeInt:
            result = value_new_bool(left_val->_float < right_val->_int);
            break;
         case TypeFloat:
            result = value_new_bool(left_val->_float < right_val->_float);
            break;
         default:
            break;
         }
         break;
      case TypeStr:
         switch (right_val->type) {
         case TypeStr:
            result = value_new_bool(0 < strcmp(left_val->_str, right_val->_str));
            break;
         default:
            break;
         }
         break;
      default:
         break;
      }
   }
   value_drop(left_val);
   value_drop(right_val);
   return result;
}

Value * builtin_gt(State * state, Node * node) {
   Value * left = eval(state, node CHILD(1));
   Value * right = eval(state, node CHILD(2));
   if (left == NULL || right == NULL) {
      value_drop(left);
      value_drop(right);
      return NULL;
   }
   Value * result = NULL;
   switch (left->type) {
   case TypeBool:
      switch (right->type) {
      case TypeBool:
         result = value_new_bool(left->_bool > right->_bool);
         break;
      case TypeInt:
         result = value_new_bool(left->_bool > right->_int);
         break;
      case TypeFloat:
         result = value_new_bool(left->_bool > right->_float);
         break;
      default:
         break;
      }
      break;
   case TypeInt:
      switch (right->type) {
      case TypeBool:
         result = value_new_bool(left->_int > right->_bool);
         break;
      case TypeInt:
         result = value_new_bool(left->_int > right->_int);
         break;
      case TypeFloat:
         result = value_new_bool(left->_int > right->_float);
         break;
      default:
         break;
      }
      break;
   case TypeFloat:
      switch (right->type) {
      case TypeBool:
         result = value_new_bool(left->_float > right->_bool);
         break;
      case TypeInt:
         result = value_new_bool(left->_float > right->_int);
         break;
      case TypeFloat:
         result = value_new_bool(left->_float > right->_float);
         break;
      default:
         break;
      }
      break;
   case TypeStr:
      switch (right->type) {
      case TypeStr:
         result = value_new_bool(0 > strcmp(left->_str, right->_str));
         break;
      default:
         break;
      }
      break;
   default:
      break;
   }
   value_drop(left);
   value_drop(right);
   return result;
}

Value * builtin_not(State * state, Node * node) {
   if (node->children.len != 2) {
      PANIC("Call error.\n");
   }
   Node * expr = node CHILD(1);
   Value * value = eval(state, expr);
   Value * result = NULL;
   if (value != NULL) {
      switch (value->type) {
      case TypeBool:
         result = value_new_bool(!value->_bool);
         break;
      default:
         break;
      }
   }
   value_drop(value);
   return result;
}

Value * builtin_and(State * state, Node * node) {
   Value * left = eval(state, node CHILD(1));
   if (value_as_bool(left)) {
      value_drop(left);
      return eval(state, node CHILD(2));
   }
   return left;
}

Value * builtin_or(State * state, Node * node) {
   Value * left = eval(state, node CHILD(1));
   if (value_as_bool(left)) {
      return left;
   }
   value_drop(left);
   return eval(state, node CHILD(2));
}

Value * builtin_list(State * state, Node * node) {
   Value * list = value_new_list();
   for (usize i = 1; i < node->children.len; i++) {
      Node * expr = node CHILD(i);
      Value * value = eval(state, expr);
      ValuePtrVec_push(&list->_list, value);
   }
   return list;
}

Value * builtin_table(State * state, Node * node) {
   Value * table = value_new_table();
   for (usize i = 1; i < node->children.len; i += 2) {
      Value * key = eval(state, node CHILD(i));
      if (key->type == TypeStr) {
         Value * value = eval(state, node CHILD(i + 1));
         table_set(&table->_table, key->_str, value);
      }
      value_drop(key);
   }
   return table;
}

Value * builtin_getitem(State * state, Node * node) {
   Value * list = eval(state, node CHILD(1));
   Value * index = eval(state, node CHILD(2));

   if (list == NULL || index == NULL) {
      value_drop(list);
      value_drop(index);
      return NULL;
   }

   Value * result = NULL;
   switch (index->type) {
   case TypeInt:
      switch (list->type) {
      case TypeStr:
         if (0 <= index->_int && index->_int < (int)strlen(list->_str)) {
            result = value_new_str_from_slice(&(Slice
            ){.str = &list->_str[index->_int], .len = 1});
         }
         break;
      case TypeList:
         if (0 <= index->_int && index->_int < (int)list->_list.len) {
            result = value_ref(list->_list.data[index->_int]);
         }
         break;
      default:
         break;
      }
      break;
   case TypeStr:
      switch (list->type) {
      case TypeTable:
         result = table_get(&list->_table, index->_str);
         break;
      default:
         break;
      }
      break;
   default:
      break;
   }

   value_drop(list);
   value_drop(index);
   return result;
}

Value * builtin_len(State * state, Node * node) {
   Value * value = eval(state, node CHILD(1));
   Value * result = NULL;
   switch (value->type) {
   case TypeStr:
      result = value_new_int((int)strlen(value->_str));
      break;
   case TypeTuple:
      result = value_new_int((int)value->_tuple.len);
      break;
   case TypeList:
      result = value_new_int((int)value->_list.len);
      break;
   default:
      break;
   }
   value_drop(value);
   return result;
}

Value * builtin_index(State * state, Node * node) {
   PANIC("TODO Index.\n");
}

Value * builtin_bool(State * state, Node * node) {
   Value * value = eval(state, node CHILD(1));
   if (value != NULL && value->type == TypeBool) {
      return value;
   }
   Value * result = value_new_bool(value_as_bool(value));
   value_drop(value);
   return result;
}

Value * builtin_int(State * state, Node * node) {
   Value * value = eval(state, node CHILD(1));
   Value * result = NULL;
   switch (value->type) {
   case TypeBool:
      result = value_new_int((int)value->_bool);
      break;
   case TypeInt:
      return value;
   case TypeFloat:
      result = value_new_int((int)value->_float);
      break;
   case TypeStr: {
      ParseIntResult parse_result = parse_int(str_as_slice(value->_str));
      if (parse_result.ok) {
         result = value_new_int(parse_result.value);
      }
      break;
   default:
      break;
   }
   }
   value_drop(value);
   return result;
}

Value * builtin_float(State * state, Node * node) {
   Value * value = eval(state, node CHILD(1));
   Value * result = NULL;
   switch (value->type) {
   case TypeBool:
      result = value_new_float((double)value->_bool);
      break;
   case TypeInt:
      result = value_new_float((double)value->_int);
      break;
   case TypeFloat:
      return value;
   case TypeStr: {
      ParseFloatResult parse_result = parse_float(str_as_slice(value->_str));
      if (parse_result.ok) {
         result = value_new_float(parse_result.value);
      }
      break;
   default:
      break;
   }
   }
   value_drop(value);
   return result;
}

Value * builtin_str(State * state, Node * node) {
   Value * value = eval(state, node CHILD(1));
   if (value == NULL) {
      return value_new_str("null");
   }
   Value * result = NULL;
   switch (value->type) {
   case TypeBool:
      if (value->_bool) {
         result = value_new_str("true");
      } else {
         result = value_new_str("false");
      }
      break;
   case TypeInt: {
#define FORMAT "%d", value->_int
      usize length = (usize)snprintf(NULL, 0, FORMAT);
      result = value_new_str_from_len((usize)length);
      snprintf(result->_str, length + 1, FORMAT);
#undef FORMAT
      break;
   }
   case TypeFloat: {
#define FORMAT "%g", value->_float
      usize length = (usize)snprintf(NULL, 0, FORMAT);
      result = value_new_str_from_len((usize)length);
      snprintf(result->_str, length + 1, FORMAT);
#undef FORMAT
      break;
   }
   case TypeStr:
      return value;
   default:
      break;
   }
   value_drop(value);
   return result;
}

Value * builtin_type(State * state, Node * node) {
   Value * value = eval(state, node CHILD(1));
   Value * result = NULL;
   if (value == NULL) {
      return value_new_str("null");
   }
   switch (value->type) {
   case TypeBool:
      result = value_new_str("bool");
      break;
   case TypeInt:
      result = value_new_str("int");
      break;
   case TypeFloat:
      result = value_new_str("float");
      break;
   case TypeStr:
      result = value_new_str("str");
      break;
   case TypeTuple:
      result = value_new_str("tuple");
      break;
   case TypeList:
      result = value_new_str("list");
      break;
   case TypeTable:
      result = value_new_str("table");
      break;
   }
   value_drop(value);
   return result;
}

Value * builtin_ternary(State * state, Node * node) {
   Value * condition = eval(state, node CHILD(1));
   Value * result = NULL;
   if (value_as_bool(condition)) {
      result = eval(state, node CHILD(2));
   } else {
      result = eval(state, node CHILD(3));
   }
   value_drop(condition);
   return result;
}

Value * eval(State * state, Node * node) {
   switch (node->type) {
   case NodeTypeLeaf:
      switch (node->token_type) {
      case TokenTypeNull:
         return NULL;
      case TokenTypeBool:
         return value_new_bool(node->_bool);
      case TokenTypeInt:
         return value_new_int(node->_int);
      case TokenTypeFloat:
         return value_new_float(node->_float);
      case TokenTypeStr:
         return value_new_str_from_literal(&node->token);
      case TokenTypeIdentifier:
         return get_variable(state, node->id);
      case TokenTypeKeyword:
         PANIC(
             "eval: Unexpected keyword in leaf node. (%.*s) \n",
             (int)node->token.len,
             node->token.str
         );
      }
      break;
   case NodeTypeBranch: {
      LEAF(tag, node CHILD(0)) {
         PANIC("Expected keyword.\n");
      }
      if (tag->token_type == TokenTypeKeyword) {
         switch (tag->_keyword) {
         case KeywordAdd:
            return builtin_add(state, node);
         case KeywordSub:
            return builtin_sub(state, node);
         case KeywordMul:
            return builtin_mul(state, node);
         case KeywordDiv:
            return builtin_div(state, node);
         case KeywordMod:
            return builtin_mod(state, node);
         case KeywordEq:
            return builtin_eq(state, node);
         case KeywordLt:
            return builtin_lt(state, node);
         case KeywordGt:
            return builtin_gt(state, node);
         case KeywordNot:
            return builtin_not(state, node);
         case KeywordAnd:
            return builtin_and(state, node);
         case KeywordOr:
            return builtin_or(state, node);
         case KeywordList:
            return builtin_list(state, node);
         case KeywordGetItem:
            return builtin_getitem(state, node);
         case KeywordLen:
            return builtin_len(state, node);
         case KeywordIndex:
            return builtin_index(state, node);
         case KeywordBool:
            return builtin_bool(state, node);
         case KeywordInt:
            return builtin_int(state, node);
         case KeywordFloat:
            return builtin_float(state, node);
         case KeywordStr:
            return builtin_str(state, node);
         case KeywordType:
            return builtin_type(state, node);
         case KeywordTernary:
            return builtin_ternary(state, node);
         case KeywordSet:
            return builtin_set(state, node);
         case KeywordTable:
            return builtin_table(state, node);
         default:
            PANIC("eval: Unexpected keyword. (%d) \n", tag->_keyword);
         }
      } else if (tag->token_type == TokenTypeIdentifier) {
         for (usize i = 1; i < node->children.len; i++) {
            Node * expr = node CHILD(i);
            Value * argument = eval(state, expr);
            ValuePtrVec_push(&state->variables, argument);
         }
         Return r = call(state, tag->id);
         return r.value;
      }
   }
   }
   PANIC("Fatal.\n");
}

Return exec(State * state, Node * node) {
   if (node->type != NodeTypeBranch) {
      PANIC("Unexpected identifier.\n");
   }
   LEAF(tag, node CHILD(0)) {
      PANIC("Expected keyword.\n");
   }
   if (tag->token_type == TokenTypeKeyword) {
      switch (tag->_keyword) {
      case KeywordSet:
         value_drop(builtin_set(state, node));
         break;
      case KeywordPrint:
         builtin_print(state, node);
         break;
      case KeywordSetItem:
         builtin_setitem(state, node);
         break;
      case KeywordPush:
         builtin_push(state, node);
         break;
      case KeywordRemove:
         builtin_remove(state, node);
         break;
      case KeywordIf: {
         if (node->children.len < 3) {
            PANIC("Malformed if.\n");
         }
         Node * expr = node CHILD(1);
         Value * condition = eval(state, expr);
         bool flag = value_as_bool(condition);
         value_drop(condition);
         Return r;
         if (flag) {
            r = exec_all(state, node CHILD(2));

         } else if (node->children.len == 5) {
            r = exec_all(state, node CHILD(4));
         } else {
            break;
         }
         if (r.returned) {
            return r;
         }
         break;
      }
      case KeywordWhile: {
         if (node->children.len < 3) {
            PANIC("Malformed while.\n");
         }
         Node * expr = node CHILD(1);
         Value * condition = eval(state, expr);
         bool flag = value_as_bool(condition);
         value_drop(condition);
         while (flag) {
            Return r = exec_all(state, node CHILD(2));
            if (r.returned) {
               return r;
            }
            Value * condition = eval(state, expr);
            flag = value_as_bool(condition);
            value_drop(condition);
         }
         break;
      }
      case KeywordFor: { /* (for VARIABLE LIST (...)) */
         if (node->children.len < 4) {
            PANIC("Malformed for.\n");
         }
         LEAF(variable, node CHILD(1)) {
            PANIC("Expected identifier.\n");
         }
         Value * list = eval(state, node CHILD(2));
         if (list->type == TypeList) {
            for (usize i = 0; i < list->_list.len; i++) {
               set_variable(state, variable->id, value_ref(list->_list.data[i]));
               Return r = exec_all(state, node CHILD(3));
               if (r.returned) {
                  value_drop(list);
                  return r;
               }
            }
         }
         value_drop(list);
         break;
      }
      case KeywordReturn:
         if (node->children.len < 2) {
            return (Return){.returned = true, NULL};
         } else {
            Value * value = eval(state, node CHILD(1));
            return (Return){.returned = true, value};
         }
      default:
         PANIC("exec: Unexpected keyword. (%d) \n", tag->_keyword);
      }
   } else if (tag->token_type == TokenTypeIdentifier) {
      for (usize i = 1; i < node->children.len; i++) {
         Node * expr = node CHILD(i);
         Value * argument = eval(state, expr);
         ValuePtrVec_push(&state->variables, argument);
      }
      Return r = call(state, tag->id);
      if (r.returned) {
         value_drop(r.value);
      }
   }
   return (Return){.returned = false};
}

Value * get_variable(State * state, usize id) {
   return value_ref(state->variables.data[state->variables_begin + id]);
}

void set_variable(State * state, usize id, Value * value) {
   usize index = state->variables_begin + id;
   value_drop(state->variables.data[index]);
   state->variables.data[index] = value;
}

Return exec_all(State * state, Node * node) {
   Return r;
   for (usize i = 0; i < node->children.len; i++) {
      r = exec(state, node CHILD(i));
      if (r.returned) {
         return r;
      }
   }
   return (Return){.returned = false};
}

/* Before call, argument values should be pushed to state.variables in order of
 * definition inside prototype. */
Return call(State * state, usize function_id) {
   Node * defun = state->functions.data[function_id];
   Node * prototype = defun CHILD(1);
   usize variables_len = defun->id;
   usize arguments_len = prototype->children.len - 1;
   usize old_variables_begin = state->variables_begin;
   state->variables_begin = state->variables.len - arguments_len;
   /* All variables are initialized to null. */
   for (usize i = 0; i < (variables_len - arguments_len); i++) {
      ValuePtrVec_push(&state->variables, NULL);
   }
   Return r = exec_all(state, defun CHILD(2));
   state->variables_begin = old_variables_begin;
   for (usize i = 0; i < variables_len; i++) {
      value_drop(state->variables.data[state->variables.len - 1]);
      ValuePtrVec_remove(&state->variables, state->variables.len - 1);
   }
   if (r.returned) {
      return r;
   } else {
      return (Return){.returned = true, .value = NULL};
   }
}

void run(State * state) {
   /* Main function does not take any arguments, no need to push any arguments.
    */
   call(state, 0);
}

void test(void) {
   ASSERT(slice_eq_str(str_as_slice("Something"), "Something"))
   ASSERT(!slice_eq_str(str_as_slice("Something123"), "Something"))
   ASSERT(!slice_eq_str(str_as_slice("Something"), "Something123"))
   ASSERT(!parse_int(str_as_slice("1.0")).ok)
   ASSERT(!parse_int(str_as_slice("1.0f")).ok)
   ASSERT(!parse_float(str_as_slice("1.0a")).ok)
   ASSERT(parse_int(str_as_slice("1")).ok)
}

int main(int argc, char ** argv) {
   if (argc == 2 && 0 == strcmp(argv[1], "--test")) {
      test();
      exit(0);
   }

   FILE * file;
   if (argc == 2) {
      file = fopen(argv[1], "r");
   } else {
      file = stdin;
   }
   State state = state_new(file);
   if (argc == 2) {
      fclose(file);
   }
   compile(&state);
   run(&state);
   state_free(&state);
}
