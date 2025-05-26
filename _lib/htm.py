from builtins import range
import re, copy

def isList(obj):
	# hasattr part is for jython
	return isinstance(obj, list) or hasattr(obj, 'tolist')
	
# Absolutely minimal template support. :)
def runTemplate(strng, **kwargs):
	def templateReplace(m):
		field = m.group(1)
		if field in kwargs:
			val = kwargs[field]
			if isinstance(val, list):
				val = ''.join(str(v) for v in val)
			else:
				val = str(val)
			return val
		return ''

	return re.sub(r'\[\[(.*?)\]\]', templateReplace, strng)

def runFileTemplate(fn, **kwargs):
	with open(fn, 'r') as fl:
		return runTemplate(fl.read(), **kwargs)

custom = {}

camelToAttr = re.compile(r'(?!_)(^|.)([A-Z])')

'''
Amazingly, this is all that's needed for generic support!

NOTE: Avoid new constructors in subclasses. If you have to, then at least
      stick to 'tagName, c, **attrs', which ought to be all that's needed. This
      may be needed for all sorts reasons (currently, so that node(<nodeinstance>, ...) works)
'''
class Node(object):
	serverAttrs = [] # The attributes which are only used for server-side processing. Defined in subclasses.
	
	# 'c' is for content
	def __init__(self, tagName, c='', *contentList, **attrs):
		self.tagName = tagName
		self.attrs = {}
		self.content = None
		self.rawTags = set(['script', 'style'])

		# Copy node if passed in
		if isinstance(tagName, Node):
			node = tagName
			self.tagName = node.tagName
			self.attrs.update(node.attrs)
			self.append(node.content)

		for k,v in attrs.items(): self.attr(k, v)
		# # Fix up class if there:
		# if "Class" in self.attrs:
			# self.attrs["class"] = self.attrs["Class"]
			# del self.attrs["Class"]
		self.append(c)
		self.append(list(contentList))
		
		self._parent = None #Only used for searches. Assumed static for now.
	
	def _startTag(self):
		s = "<"+self.tagName
		
		# Handle attributes
		for k,v in self.attrs.items():
			# FIX: Empty string shouldn't force attribute to be ignored (e.g. <option value="">text</option> is valid)
			# Workaround for now is to use "\0" to represent empty string
			if k not in self.serverAttrs \
					and v is not None and v != "": # None's and blank strings means ignore attribute
				if v=="\0": v = ""
				# Escape double quotes in the value, because you never want raw double quotes
				s += " " + k + '="'+str(v).replace('"', '&quot;')+'"';
		s += ">"
		
		return s
	
	def _contentRecur(self, content):
		s = ''
		
		# Handle content
		if isinstance(content, Node):
			s = str(content)
		elif isList(content):
			# for el in content:
				# s += self._contentRecur(el)
			s = ''.join(self._contentRecur(el) for el in content)
		else:
			isRawHtml = isinstance(content, RawHtml)
			if not isRawHtml and self.tagName in self.rawTags:
				content = RawHtml(content)
				isRawHtml = True
			
			toConvert = content
			if isRawHtml:
				toConvert = content.str
			# Content might be *anything* that can be converted to a string. Simple.
			# Except, the 'str' conversion treats unicode specially (for no good reason I can think of).
			# That is, it throws an exception in some cases, when it should never throw an exception.
			# Ever. The semantics of 'str' in Python are such that it means "convert *anything* into
			# a string of bytes, no questions asked" --- and those firm semantics are
			# broken in one of the most important cases, causing the program to crash, rather
			# than noting the error and moving on!
			contentStr = None
			try:
				contentStr = str(toConvert)
			except:
				try:
					contentStr = toConvert.encode('utf-8', 'replace')
				except:
					contentStr = "[str convert error]"

			s = contentStr if isRawHtml else toHtml(contentStr)
			
		return s
	
	def _content(self):
		return self._contentRecur(self.content)

	def _endTag(self):
		return "</"+self.tagName+">"

	def __str__(self):
		s  = self._startTag()

		s += self._content()		
		
		s += self._endTag()
		
		return s
	
	def str(self):
		return str(self)
	
	# Hmm, Jython is using repr for print for some reason
	def __repr__(self):
		return self.__str__()
	
	# Get or set an attribute. 
	def attr(self, name, value = None):
		# Replace upper case letters with dash then lower case (ala JS -> CSS),
		# unless preceded by underscore
		#name = re.sub(r'(?!_)(^|.)([A-Z])', lambda x: x.group(1)+"-"+x.group(2).lower(), name)
		# Special case "Class", because "class" is a reserved keyword in python
		name = camelToAttr.sub(lambda x: x.group(1)+"-"+x.group(2).lower(), name) if name != 'Class' else 'class'
		# Remove underscores
		#name = re.sub(r'_', '', name)
		name = name.replace('_', '')
		
		if value is not None:
			self.attrs[name] = value
			return self
		else:
			return self.attrs.get(name)
	
	def removeAttr(self, name):
		del self.attrs[name]
		return self
	
	def hasAttr(self, name):
		name = camelToAttr.sub(lambda x: x.group(1)+"-"+x.group(2).lower(), name) if name != 'Class' else 'class'
		# Remove underscores
		#name = re.sub(r'_', '', name)
		name = name.replace('_', '')
		
		return name in self.attrs
	
	def addClass(self, cls):
		if "class" not in self.attrs:
			self.attrs["class"] = ""
		# Remove it if already there:
		self.attrs["class"] = re.sub(r'\b'+cls+r'\b', '', self.attrs["class"])
		# Add it:
		self.attrs["class"] += " " + cls
		
		# Chain
		return self
	
	def removeClass(self, cls):
		if "class" not in self.attrs:
			self.attrs["class"] = ""
		# Remove it if already there:
		self.attrs["class"] = re.sub(r'\b'+cls+r'\b', '', self.attrs["class"])
		
		# Remove attribute altogether if empty
		if not self.attrs["class"]:
			del self.attrs["class"]
		
		# Chain
		return self
	
	def hasClass(self, cls):
		if "class" not in self.attrs:  return False
		return bool(re.search(r'\b'+cls+r'\b', self.attrs["class"]))

	def testClone(self):
		t = node("div.joinTemplate", c=[
			node("select", data=["a","b"]),
		])
		
		t2 = t.clone()

		t.content[0].attr("value", "abc")
	
	def clone(self):
		# Not sure if Jython has a bug with deepcopy or if python doesn't support it.
		# Anyway, implementing here.
		
		newNode = node(self.tagName)
		for k,v in self.attrs.items():
			if isinstance(v, Node):
				newNode.attrs[k] = v.clone()
			else:
				newNode.attrs[k] = v
		
		if self.content is not None:
			if isList(self.content):
				newNode.content = []
				for v in self.content:
					if isinstance(v, Node):
						newNode.content.append(v.clone())
					else:
						newNode.content.append(v)
				
			elif isinstance(self.content, Node):
				newNode.content = self.content.clone()
			else:
				newNode.content = self.content
		
		return newNode
	
	def after(self, *items):
		selfI = self._parent.content.index(self)
		for item in reversed(items):
			self._parent.content.insert(selfI+1, item)
		
		return self
	
	def before(self, *items):
		selfI = self._parent.content.index(self)
		for item in reversed(items):
			self._parent.content.insert(selfI, item)
		
		return self
	
	# Append content
	def append(self, *items):
		if self.content is None:
			# I'm not sure collapsing singleton lists is really necessary...
			if len(items)==1:
				self.content = items[0]
			else:
				self.content = items
		else:
			if not isList(self.content):
				self.content = [self.content]

			self.content.extend(items)
		
		return self
	
	# Prepend content
	def prepend(self, *items):
		c = self.content
		self.content = list(items)
		self.content.extend(c)
	
	def childNodes(self):
		children = []
		for item in self.content:
			if type(item) is Node:
				children.append(item)
		
		return children
	
	def appendNode(self, tagName, *args, **kwargs):
		self.append(node(tagName, *args, **kwargs))
	
	def _localMatch(self, sel):
		m = re.findall(r'([\.#:]?)([\w\d_-]+)', sel)
		isMatched = True
		for matching in m:
			if matching[0]==".":
				if not self.hasClass(matching[1]):
					isMatched = False
					break
			elif matching[0]=="#":
				if "id" not in self.attrs or self.attrs["id"] != matching[1]:
					isMatched = False
					break
			elif matching[0]=="":
				if self.tagName != matching[1]:
					isMatched = False
					break
		return isMatched
	
	# Not sure how much I should support here. Currently supported:
	# - tag
	def match(self, selector):
		sels = re.split(r'\s*,\s*', selector.strip())
	
		# Any comma-separated selector match is a success
		for sel in sels:
			selMatch = True
			parts = re.split(r'\s+', sel.strip())
			target = parts[-1]
			if self._localMatch(target):
				testAgainst = self._parent
				for part in reversed(parts[:-1]):
					partMatched = False
					while testAgainst:
						if testAgainst._localMatch(part):
							partMatched = True
							break
						testAgainst = testAgainst._parent
					if not partMatched:
						selMatch = False
						break
				if selMatch:
					return True
		
		return False
	
	def flattenList(self, lst):
		newList = []
		toFlatten = [lst]
		while len(toFlatten)>0:
			next = toFlatten.pop(0)
			
			if isinstance(next, list):
				toFlatten = next + toFlatten
			else:
				newList.append(next)
		
		return newList
		
	def find(self, sel):
		els = []
		toSearch = [self]
		while len(toSearch)>0:
			el = toSearch.pop(0)
			#rint(el.tagName if hasattr(el,'tagName') else 'notag')
			if isinstance(el,list):
				toSearch.extend(el)
			elif hasattr(el,'match') and el.match(sel):
				els.append(el)
			if hasattr(el, "content"):
				#rint("adding content:", el.content)
				contentList = self.flattenList(el.content)
				for item in contentList:
					if hasattr(item, "_parent"):
						item._parent = el
				toSearch.extend(contentList)
			
		return els
	
	# Get the content or replace the content with the given items
	# FIX: Use the name 'content'
	def html(self, *items):
		if len(items)==0:
			return self.content
		else:
			self.content = None
			self.append(*items)

			return self

def node(tagName, c='', *contentList, **attrs):
	if isinstance(tagName, Node):
		return tagName.__class__(tagName, c, **attrs)

	m = re.findall(r'[\.#]?[\w\d_-]+', tagName)
	tagName = m.pop(0)
	classes = ""
	for attr in m:
		if attr[0]==".":
			classes += " " + attr[1:]
		elif attr[0]=="#":
			attrs["id"] = attr[1:]
	if classes != "": attrs["class"] = classes
	
	if tagName in custom:
		return custom[tagName](tagName, c, *contentList, **attrs)
	else:
		return Node(tagName, c, *contentList, **attrs)

# http://stackoverflow.com/questions/312443/how-do-you-split-a-list-into-evenly-sized-chunks-in-python
def chunks(l, n):
    """ Yield successive n-sized chunks from l.
    """
    for i in range(0, len(l), n):
        yield l[i:i+n]

# When setting the selected option, 'str' is applied first before comparison
class Select(Node):
	serverAttrs = ['data']
	
	def _content(self):
		s = ""

		# insert manually specified options first
		s += super(Select,self)._content()

		if self.hasAttr("data"):
			data = self.attr("data")
			selected = self.attr("selected")
			if isList(data) and len(data)>0:
				if not isList(data[0]):
					data = chunks(data, 1)
				for row in data:
					s += str(node("option", value=row[0], selected="selected" if str(selected)==str(row[0]) else None, c=row[1] if len(row)>1 else row[0]))
			# Assume record set
			elif hasattr(data, "next"):
				while next(data):
					s += str(node("option", value=data.getString(1), selected="selected" if str(selected)==data.getString(1) else None, c=data.getString(2))) # Allow single column recordset
		
		return s
custom["select"] = Select

tableHandlers = {}

class Table_checkbox:
	handlerName = "checkbox"
	
	def __init__(self, tdAttr = {}, inputAttr = {}):
		self.tdAttr = tdAttr
		self.inputAttr = inputAttr
	
	def handleHeader(self, i, fieldName):
		return node("th", dataReadonly = "readonly", dataField = fieldName, dataHandler = "checkbox")
	
	def handle(self, val, row, i, pkI = None):
		return node("td", c=[
			node("input", type="checkbox", checked = "checked" if val else None, value = row[pkI] if pkI is not None else "on", **self.inputAttr)
		], **self.tdAttr)

tableHandlers["checkbox"] = Table_checkbox

class TableHandlerFunc:
	def __init__(self, func):
		self.func = func
		
	def handle(self, val, row, i):
		return self.func(val, row, i)

class Table(Node):
	serverAttrs = [
		"name", # (opt) Creates a hidden form element with the given name
		"data", # (opt) A database table-like data source to fill the table with: a recordset, 2D array or {header:...,data:...} object
		"headers", # (opt) Only used with the 'data' attribute. Specifies the field names/headers (as array).
		"headerLabels", # (opt) A dict (field name => label) or array with labels for the headers
		"pk", # (opt) The primary key, used to identify rows. Omitted by default.
		"keepPk", # Don't omit the primary key
		"selector", # (opt) Boolean or String. Whether to show a checkbox for each row
		            # that can be used as a row selector. If string given, used as name for checkbox.
		"handlers", # (opt) Handlers for the cells, based on headers given {header: handler, ...}. Can be names of 'tableHandlers',
		            # objects (with a handle/handleHeader method) or functions (equiv to just handle method)
		"readonly", # (opt) A list of readonly fields
		"omit", # (opt) A list of fields to ignore when creating the table,
		"hidden", # (opt) A list of fields included as normal (so can be read/changed/saved), but hidden from display
		"group1",   # Simple row grouping, based on 1 common (contiguous) values in column. Group column is then omitted.
		"rowAdapter", # A function that is applied to all rows just before they are stringified. Is passed two parameters: the tr node and isHeader?
		"defaultDataCellHandler", # A function that is applied to all data cells. Must be full node function
		                          # e.g. lambda val: n('td', toHtml(val))
	]
	
	def __init__(self, tagName, c='', *contentList, **attrs):
		super().__init__(tagName, c, *contentList, **attrs)
		self.make()
	
	def old_startTag(self):
		if self.hasAttr("name"):
			self.attr("data-form-control", self.attr("name"))
		return super(Table, self)._startTag()
	
	def make(self):
		if self.hasAttr("name"):
			self.attr("data-form-control", self.attr("name"))
		# insert manually specified content first
		if self.hasAttr("name"):
			self.append(node("input", type="hidden", name=self.attr("name")))
			
		hasSelector = False
		selectorHandler = None
		if self.hasAttr("selector"):
			hasSelector = bool(self.attr("selector"))
			selectorName = self.attr("selector") if isinstance(self.attr("selector"),basestring) else None
			selectorHandler = Table_checkbox(tdAttr={"Class": "selector"}, inputAttr={"name": selectorName})
		
		if self.hasAttr("data"):
			data = self.attr("data")

			# Headers only make sense if data attribute set
			headers = None
			if self.hasAttr("headers"):
				headers = self.attr("headers")
			
			omit = self.attr("omit") or []
			hidden = self.attr("hidden") or []
			
			defaultDataCellHandler = self.attr("defaultDataCellHandler")
			
			# If data has a method called 'convertToDataHeaders', use it to create the right interface			
			if hasattr(data, "convertToDataHeaders"):
				data = data.convertToDataHeaders()

			# If given a dict, decompose into data/headers
			if isinstance(data, dict):
				headers = data["headers"] if not headers else headers
				data = data["data"]
			
			# Header lookup
			headersPos = None
			if headers:
				headersPos = dict((v,k) for k,v in enumerate(headers))
				
			# If given an array of dicts, assume first dict canonical, and extract headers and data
			# (This now works well in Python, because dicts are ordered by insertion by default)
			if len(data)>0 and isinstance(data[0], dict):
				headers = list(data[0].keys())
				headersPos = dict((v,k) for k,v in enumerate(headers))
				newData = []
				for row in data:
					newRow = [None for i in range(len(row))]
					for k,v in row.items():
						newRow[headersPos[k]] = v
					newData.append(newRow)
				
				data = newData
			
			headerLabels = self.attr("headerLabels") if self.hasAttr("headerLabels") else {}
			if headers and isinstance(headerLabels, list):
				headerLabels = dict(zip(headers, headerLabels))
			def getHeaderLabel(header):
				return RawHtml(headerLabels[header]) if header in headerLabels else header
				
			# If passed a row adapter, use it
			if self.hasAttr("rowAdapter"):
				rowAdapter = self.attr("rowAdapter")
			else:
				rowAdapter = lambda tr,rowDataIfTd: tr
			
			# Setup grouping, and omit group column from display
			group1Column = self.attr("group1")
			if group1Column:
				group1Column = headersPos[group1Column] if isinstance(group1Column, basestring) else group1Column
				omit.append(self.attr("group1"))

			selected = self.attr("selected")
			dataHandler = {}

			# Find the primary key if one was specified
			pkI = None
			pkName = None
			if self.hasAttr("pk"):
				pkI = self.attr("pk")
				try: int(pkI)
				except:
					if headers:
						pkI = headers.index(pkI)
					else:
						pkI = 0
				if headers:
					pkName = headers[pkI]

			# Omit PK, unless requested to keep it
			if self.hasAttr("pk") and "keepPk" not in self.attrs:
				omit.append(pkI)
			
			# Write out the header row (if present)
			if headers:
				tr = node("tr.header", dataPkName = pkName)
				if hasSelector:
					tr.append(selectorHandler.handleHeader(-1, "_sel_"))
				for headerI, header in enumerate(headers):
					if header in omit or headerI in omit: continue
					
					headerLabel = getHeaderLabel(header)
					handler = None
					if self.hasAttr("handlers"):
						handler = self.attr("handlers").get(header)
					if handler in tableHandlers:
						dataHandler[headerI] = tableHandlers[handler]()
					else:
						if hasattr(handler,"handle"):
							dataHandler[headerI] = handler
							handler = None
						elif callable(handler):
							dataHandler[headerI] = TableHandlerFunc(handler)
							handler = None

					readonly = None
					if self.hasAttr("readonly") and header in self.attr("readonly"):
						readonly = "readonly"

					th = node("th", dataHandler=handler, dataReadonly=readonly, dataField=header, c=headerLabel)
					if header in hidden or headerI in hidden:
						th.addClass('hidden')
					tr.append(th)
				tr = rowAdapter(tr, 0)
				self.append(node('thead',tr))


			# Write out the data
			lastGroup1Value = None
			tbody = node('tbody')
			for rowI, row in enumerate(data):
				# Add group headers
				if group1Column is not None:
					group1Value = row[group1Column]
					if group1Value != lastGroup1Value:
						tr = node("tr.group1", c=[
							node("th", colspan=len(row), c=group1Value)
						])
						self.append(tr)
						lastGroup1Value = group1Value
				tr = node("tr", dataPk=row[pkI] if pkI is not None else None)
				if hasSelector:
					tr.append(selectorHandler.handle(None,row,-1,pkI))
				rowDict = _RowDict(row,headersPos)
				for cellI,cell in enumerate(row):
					if cellI in omit or (headers and headers[cellI] in omit): continue

					if cell is None: cell = ""

					newTd = None
					if cellI in dataHandler:
						newTd = dataHandler[cellI].handle(cell, rowDict, cellI)
					else:
						if defaultDataCellHandler:
							newTd = defaultDataCellHandler(cell, rowI, cellI)
						else:
							newTd = node("td", cell)
					if cellI in hidden or (headers and headers[cellI] in hidden):
						newTd.addClass('hidden')
						
					tr.append(newTd)
					

				tr = rowAdapter(tr, rowDict)
				tbody.append(tr)
				
			
			self.append(tbody)
custom["table"] = Table

class _RowDict(object):
	def __init__(self, rowData, fieldMap):
		self.rowData = rowData
		self.fieldMap = fieldMap
	
	def __getitem__(self, key):
		if isinstance(key, basestring):
			return self.rowData[self.fieldMap[key]]
		else:
			return self.rowData[key]
	
	def __setitem__(self, key, value):
		if isinstance(key, basestring):
			self.rowData[self.fieldMap[key]] = value
		else:
			self.rowData[key] = value
	
	def __len__(self):
		return len(self.rowData)
	
	def __iter__(self):
		return iter(self.rowData)
	
	def keys(self):
		return self.fieldMap.keys()
	
	def values(self):
		return self.rowData
	
	def itervalues(self):
		return iter(self.rowData)

def checkbox(name, label = None):
	if label is None: label = name
	return node("div.field", c=[
		node("label", label),
		node("input", type="checkbox", checked="checked", name=name, id=name),
	])

# Strip out leading indentation, based on first indented line
def st(strng):
	m = re.search(r'^([ \t]{1,})', strng, flags=re.MULTILINE)
	initialSpaces = ""
	if m:
		initialSpaces = m.group(1)
	# Strip out found spaces in all lines, and starting/ending whitespace
	return re.sub("^"+initialSpaces, '', strng, flags=re.MULTILINE).strip()

def toHtml(strng):
	if not strng: return strng
	strng = str(strng)
	strng = strng.replace('&', '&amp;')
	strng = strng.replace('>', '&gt;')
	strng = strng.replace('<', '&lt;')
	strng = strng.replace('"', '&quot;')
	return strng

# This does nothing other than flag the string saying it should be treated as raw html
class RawHtml:
	def __init__(self, str):
		self.str = str
	def __str__(self):
		return self.str

# 'n' is the standard shortcut for 'node'
n = node