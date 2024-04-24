from lark import Lark, Transformer, v_args
import ast
import json

query = r'''
%import common.WS
%ignore WS
%import common.SIGNED_NUMBER
%import common.ESCAPED_STRING
%import common.CNAME

?query : negation
       | intersection
       | union
       | grouped
       {include_flags}
       {include_features}
       | comparison

negation : "-" grouped
         {flag_negation}

intersection : query "," query
union :  query "|" query

?grouped : "(" query ")"
'''

feature_addons = r'''
comparison : feature_shift comparator feature_shift

?feature_list : feature_shift
              | feature_shift "," feature_list

json_feature : JSON_KEY

JSON_KEY : ("." CNAME)+

?feature_atom : feature
              | "(" feature_shift ")"
              | SIGNED_NUMBER -> number
              | ESCAPED_STRING -> string

?feature_exp : feature_atom
              | feature_exp OPERATOR_EXP feature_atom -> feature_op
?feature_scale : feature_exp
                | feature_scale OPERATOR_SCALE feature_exp -> feature_op
?feature_shift : feature_scale
          | feature_atom OPERATOR_SHIFT feature_scale -> feature_op

operator : OPERATOR_EXP | OPERATOR_SCALE | OPERATOR_SHIFT
comparator : COMPARATOR -> operator

COMPARATOR : "<" | ">" | "<=" | ">=" | "=" | "=="
OPERATOR_EXP : "^"
OPERATOR_SCALE : "*" | "/"
OPERATOR_SHIFT : "+" | "-"

'''


OPERATORS = {
    '+': lambda x,y: x + y,
    '-': lambda x,y: x - y,
    '*': lambda x,y: x * y,
    '/': lambda x,y: x / y,
    '^': lambda x,y: x ** y,
    '>': lambda x,y: x > y,
    '>=': lambda x,y: x >= y,
    '<': lambda x,y: x < y,
    '<=': lambda x,y: x <= y,
    '=': lambda x,y: x == y,
    '==': lambda x,y: x == y
}

def get_field(key, data):
    for field in key.split('.')[1:]:
        data = data[field]
    return data


@v_args(inline=True)
class QueryFilter(Transformer):
    def __init__(self, query_customization, dataset, require_flags=True, require_features=True):
        if not require_flags and not require_features:
            raise Exception('cannot construct parser with neither require_flags nor require_features')

        self.dataset = dataset
        self.universe = set(dataset.keys())
        
        include_flags = '| flag' if require_flags else ''
        flag_negation = '| "-" flag' if require_flags else ''
        include_features = '| comparison' if require_features else ''
        addons = feature_addons if require_features else ""

        template = query.format(include_flags=include_flags, include_features=include_features, flag_negation=flag_negation)
        grammar = f'{template}\n{query_customization}\n{addons}'

        self.query_parser = Lark(grammar, start="query")

    def __call__(self, query_string):
        parse_tree = self.query_parser.parse(query_string)
        return self.transform(parse_tree)

    def negation(self, child):
        return self.universe - child
    
    def intersection(self, left, right):
        return left.intersection(right)
    
    def union(self, left, right):
        return left.union(right)
    
    def operator(self, op):
        return OPERATORS[op]

    def comparison(self, left_fn, operator, right_fn):
        result = set()
        for id, element in self.dataset.items():
            if operator(left_fn(element), right_fn(element)):
                result.add(id)
        
        return result
    
    def feature_list(self, *args):
        return args
    
    def number(self, value):
        n = float(value)
        return lambda x: n
    
    def string(self, value):
        value = ast.literal_eval(value)
        return lambda x: value

    def feature_op(self, left_fn, operator, right_fn):
        op_fn = OPERATORS[operator]
        return lambda x: op_fn(left_fn(x), right_fn(x))
    
    def json_feature(self, key_path):
        return lambda x: get_field(key_path, x)
