import re, sys

import numpy as np
import pandas as pd

from concurrent.futures import ThreadPoolExecutor
from collections import defaultdict, deque


def topological_sort(dependencies):
    in_degree = defaultdict(int)
    for node in dependencies:
        for dep in dependencies[node]:
            in_degree[dep] += 1

    queue = deque([node for node in dependencies if in_degree[node] == 0])
    sorted_order = []

    while queue:
        node = queue.popleft()
        sorted_order.append(node)

        for dep in dependencies[node]:
            in_degree[dep] -= 1
            if in_degree[dep] == 0:
                queue.append(dep)

    if len(sorted_order) == len(dependencies):
        return sorted_order
    else:
        return None 

def parse_expr(expr, vars):
	def substitute_vars(s):
		pattern = r'\b(' + '|'.join(re.escape(var) for var in vars) + r')\b'
		return re.sub(pattern, lambda m: f'd["{m.group(1)}"]', s)

	def clean_scientific_notation(s):
		return re.sub(r'e[_](\d+)', r'e-\1', s)

	def parse_if_recursive(expr):
		pattern = re.compile(r"If\(([^,]+),([^,]+),([^)]+)\)")
		while True:
			match = pattern.search(expr)
			if not match:
				break
			cond, tval, fval = match.group(1), match.group(2), match.group(3)
			cond = re.sub(r'(?<![=!<>])=(?!=)', '==', cond)
			cond, tval, fval = cond.strip(), tval.strip(), fval.strip()
			replacement = f"({tval} if {cond} else {fval})"
			expr = expr[:match.start()] + replacement + expr[match.end():]
		return expr
	
	def convert_switch(match):
		args = [x.strip() for x in match.group(1).split(',')]
		key = args[0]
		pairs = args[1:]

		if len(pairs) % 2 == 0:
			default = '0'
		else:
			default = pairs.pop()

		dict_entries = ', '.join(f"{pairs[i]}: {pairs[i+1]}" for i in range(0, len(pairs), 2))
		return f"{{{dict_entries}}}.get({key}, {default})"


	expr = clean_scientific_notation(expr)
	expr = expr.replace("nan", "np.nan")

	expr = parse_if_recursive(expr)
	expr = re.sub(r"Switch\((.+?)\)", convert_switch, expr)

	expr = substitute_vars(expr)

	expr = expr.replace("Uniform(", "np.random.uniform(")
	expr = expr.replace("Normal(", "np.random.normal(")
	expr = expr.replace("Trim(", "np.clip(")
	expr = expr.replace("Triangular(", "np.random.triangular(")
	expr = expr.replace("Bernoulli(", "np.random.binomial(1, ")
	expr = expr.replace("Min(", "min(")
	expr = expr.replace("Max(", "max(")
	expr = expr.replace("^", "**")

	# print(expr)
	return expr





class EquationModel:
	def __init__(self, equations):
		self.model = {}
		self.dependencies = defaultdict(list)
		self.samples = None
		self.updated = False

		self.model = {eq.split("=", 1)[0].strip() : None for eq in equations}
		
		for eq in equations:
			var, expr = eq.split("=", 1)
			self.update_equation(var, expr)

		
	def update_equation(self, var, expr):
		self.updated = False
		vars = self.model.keys()
		
		for dep in re.findall(r'\b(' + '|'.join(re.escape(var) for var in vars) + r')\b', expr):
			self.dependencies[dep].append(var.strip())
					
		self.model[var.strip()] = eval(f"lambda d: {parse_expr(expr, vars)}")

	def sample(self, _):
		values = {}
		
		for var in self.sorted_vars:
			values[var] = self.model[var](values)
				
		return values
			
	def update(self, num_samples = 100):
		if not self.updated:
			self.sorted_vars = topological_sort(self.dependencies)
			# self.samples = pd.DataFrame([self.sample() for _ in range(num_samples)])
			with ThreadPoolExecutor() as executor:
				self.samples = pd.DataFrame(list(executor.map(self.sample, [None] * num_samples)))
			self.updated = True
		

	def get(self, var):
		self.update()
		return self.samples[var]




# import re, sys

# import numpy as np
# import pandas as pd

# from concurrent.futures import ThreadPoolExecutor
# from collections import defaultdict


# def parse_expr(expr, vars):
# 	def substitute_vars(s):
# 		pattern = r'\b(' + '|'.join(re.escape(var) for var in vars) + r')\b'
# 		return re.sub(pattern, lambda m: f'd["{m.group(1)}"]', s)

# 	def clean_scientific_notation(s):
# 		return re.sub(r'e[_](\d+)', r'e-\1', s)

# 	def parse_if_recursive(expr):
# 		pattern = re.compile(r"If\(([^,]+),([^,]+),([^)]+)\)")
# 		while True:
# 			match = pattern.search(expr)
# 			if not match:
# 				break
# 			cond, tval, fval = match.group(1), match.group(2), match.group(3)
# 			cond = re.sub(r'(?<![=!<>])=(?!=)', '==', cond)
# 			cond, tval, fval = cond.strip(), tval.strip(), fval.strip()
# 			replacement = f"({tval} if {cond} else {fval})"
# 			expr = expr[:match.start()] + replacement + expr[match.end():]
# 		return expr
	
# 	def convert_switch(match):
# 		args = [x.strip() for x in match.group(1).split(',')]
# 		key = args[0]
# 		pairs = args[1:]

# 		if len(pairs) % 2 == 0:
# 			default = '0'
# 		else:
# 			default = pairs.pop()

# 		dict_entries = ', '.join(f"{pairs[i]}: {pairs[i+1]}" for i in range(0, len(pairs), 2))
# 		return f"{{{dict_entries}}}.get({key}, {default})"


# 	expr = clean_scientific_notation(expr)
# 	expr = expr.replace("nan", "np.nan")

# 	expr = parse_if_recursive(expr)
# 	expr = re.sub(r"Switch\((.+?)\)", convert_switch, expr)

# 	expr = substitute_vars(expr)

# 	expr = expr.replace("Uniform(", "np.random.uniform(")
# 	expr = expr.replace("Normal(", "np.random.normal(")
# 	expr = expr.replace("Trim(", "np.clip(")
# 	expr = expr.replace("Triangular(", "np.random.triangular(")
# 	expr = expr.replace("Bernoulli(", "np.random.binomial(1, ")
# 	expr = expr.replace("Min(", "min(")
# 	expr = expr.replace("Max(", "max(")
# 	expr = expr.replace("^", "**")

# 	# print(expr)
# 	return expr





# class EquationModel:
# 	def __init__(self, equations):
# 		self.model = {}
# 		self.dependencies = defaultdict(list)
# 		self.samples = None
# 		self.updated = False

# 		for eq in equations:
# 			var, expr = eq.split("=", 1)
# 			self.model[var.strip()] = None	
		
# 		for eq in equations:
# 			var, expr = eq.split("=", 1)
# 			self.update_equation(var, expr)

# 		# vars = [eq.split("=", 1)[0].strip() for eq in equations]
		
# 		# for eq in equations:
# 		# 	var, expr = eq.split("=", 1)
# 		# 	self.model[var.strip()] = eval(f"lambda d: {parse_expr(expr, vars)}")

		
# 	def update_equation(self, var, expr):
# 		self.updated = False
# 		vars = self.model.keys()
# 		for dep in re.findall(r'\b(' + '|'.join(re.escape(var) for var in vars) + r')\b', expr):
# 			self.dependencies[dep].append(var.strip())
					
# 		self.model[var.strip()] = eval(f"lambda d: {parse_expr(expr, vars)}")

# 	def sample(self, _):
# 		values = {}
		
# 		pending = set(self.model.keys())
		
# 		while pending:
# 			for var in list(pending):
# 				try:
# 					values[var] = self.model[var](values)
# 					pending.remove(var)			
# 				except KeyError:
# 					continue
				
# 		return values
			
# 	def update(self, num_samples = 100):
# 		if not self.updated:
# 			# self.samples = pd.DataFrame([self.sample() for _ in range(num_samples)])
# 			with ThreadPoolExecutor() as executor:
# 				self.samples = pd.DataFrame(list(executor.map(self.sample, [None] * num_samples)))
# 			self.updated = True
		

# 	def get(self, var):
# 		self.update()
# 		return self.samples[var]

