# Refactoring Catalog

Concise reference of refactoring techniques organized by pillar. Use this to select the right technique for each finding.

---

## Pillar 1: Complexity Simplification

### Extract Method

**When**: A function is too long or a block of code has a distinct purpose.

```
# Before
def process_order(order):
    # validate
    if not order.items:
        raise ValueError("empty")
    if order.total < 0:
        raise ValueError("negative")
    # calculate discount
    discount = 0
    if order.total > 100:
        discount = order.total * 0.1
    # ... 20 more lines

# After
def process_order(order):
    validate_order(order)
    discount = calculate_discount(order)
    # ... cleaner flow
```

### Guard Clauses

**When**: Deep nesting caused by if/else chains checking preconditions.

```
# Before
def handle(request):
    if request:
        if request.user:
            if request.user.is_active:
                return do_work(request)
    return None

# After
def handle(request):
    if not request:
        return None
    if not request.user:
        return None
    if not request.user.is_active:
        return None
    return do_work(request)
```

### Compose Method

**When**: A function mixes multiple abstraction levels, making it hard to follow.

```
# Before
def generate_report(data):
    # 50 lines mixing filtering, formatting, I/O

# After
def generate_report(data):
    filtered = filter_relevant(data)
    formatted = format_for_output(filtered)
    write_report(formatted)
```

### Replace Conditional with Polymorphism

**When**: A switch/if-else selects behavior based on a type discriminator.

```
# Before
def calculate_area(shape):
    if shape.type == "circle":
        return pi * shape.radius ** 2
    elif shape.type == "rect":
        return shape.width * shape.height

# After
class Circle:
    def area(self): return pi * self.radius ** 2

class Rect:
    def area(self): return self.width * self.height
```

### Strategy Pattern

**When**: An algorithm varies at runtime and is selected via conditionals.

```
# Before
def export(data, fmt):
    if fmt == "csv":
        # 20 lines of CSV logic
    elif fmt == "json":
        # 20 lines of JSON logic

# After
exporters = {"csv": CsvExporter(), "json": JsonExporter()}
exporters[fmt].export(data)
```

---

## Pillar 2: Code Reduction

### Remove Dead Code

**When**: Functions, imports, variables, or branches are never reached or used.

```
# Before
import os, sys, json  # sys never used
def old_handler(): ...  # never called

# After
import os, json
# old_handler removed
```

### DRY Extraction

**When**: Similar code blocks appear in 2+ locations.

```
# Before
def create_user(data):
    validate_email(data["email"])
    validate_name(data["name"])
    db.insert("users", data)

def create_admin(data):
    validate_email(data["email"])
    validate_name(data["name"])
    data["role"] = "admin"
    db.insert("users", data)

# After
def validate_person(data):
    validate_email(data["email"])
    validate_name(data["name"])

def create_user(data):
    validate_person(data)
    db.insert("users", data)

def create_admin(data):
    validate_person(data)
    data["role"] = "admin"
    db.insert("users", data)
```

### Introduce Parameter Object

**When**: Multiple functions pass the same group of parameters together.

```
# Before
def search(query, page, page_size, sort_by, sort_order): ...
def count(query, page, page_size, sort_by, sort_order): ...

# After
class SearchParams:
    query: str
    page: int
    page_size: int
    sort_by: str
    sort_order: str

def search(params: SearchParams): ...
def count(params: SearchParams): ...
```

### Replace Verbose Idiom

**When**: Code uses a manual loop/pattern where a built-in or standard library call suffices.

```
# Before
result = []
for item in items:
    if item.active:
        result.append(item.name)

# After
result = [item.name for item in items if item.active]
```

---

## Pillar 3: Separation of Responsibilities

### Extract Class

**When**: A class has fields and methods that cluster into two or more distinct responsibilities.

```
# Before
class Order:
    def calculate_total(self): ...
    def format_invoice_pdf(self): ...
    def send_email_notification(self): ...

# After
class Order:
    def calculate_total(self): ...

class InvoiceFormatter:
    def format_pdf(self, order): ...

class OrderNotifier:
    def send_email(self, order): ...
```

### Move Method

**When**: A method uses more data from another class than its own.

```
# Before
class Report:
    def avg_salary(self, department):
        total = sum(e.salary for e in department.employees)
        return total / len(department.employees)

# After (method moved to Department)
class Department:
    def avg_salary(self):
        total = sum(e.salary for e in self.employees)
        return total / len(self.employees)
```

### Facade Pattern

**When**: Client code interacts with many subsystem classes directly, creating coupling.

```
# Before
db = Database()
cache = Cache()
validator = Validator()
# client calls all three in sequence everywhere

# After
class ServiceFacade:
    def __init__(self):
        self.db = Database()
        self.cache = Cache()
        self.validator = Validator()

    def save(self, data):
        self.validator.check(data)
        self.db.insert(data)
        self.cache.invalidate(data.key)
```

### Template Method

**When**: Multiple subclasses follow the same algorithm skeleton but vary specific steps.

```
# Before
class CsvImporter:
    def run(self):
        data = self.read_csv()
        cleaned = self.clean(data)
        self.save(cleaned)

class JsonImporter:
    def run(self):
        data = self.read_json()
        cleaned = self.clean(data)
        self.save(cleaned)

# After
class BaseImporter:
    def run(self):
        data = self.read()    # abstract
        cleaned = self.clean(data)
        self.save(cleaned)

class CsvImporter(BaseImporter):
    def read(self): ...  # CSV-specific

class JsonImporter(BaseImporter):
    def read(self): ...  # JSON-specific
```

### Layer Separation

**When**: Business logic, I/O, and presentation are interleaved in the same function or module.

```
# Before
def handle_request(req):
    data = db.query("SELECT ...")      # data access
    if data.amount > 1000:             # business logic
        data.status = "flagged"
    return json.dumps(data.__dict__)   # presentation

# After
# repository.py
def get_transaction(id): return db.query(...)

# service.py
def flag_if_needed(txn):
    if txn.amount > 1000:
        txn.status = "flagged"

# handler.py
def handle_request(req):
    txn = get_transaction(req.id)
    flag_if_needed(txn)
    return serialize(txn)
```
