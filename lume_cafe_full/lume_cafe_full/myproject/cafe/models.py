from django.db import models
from django.utils import timezone

class Customer(models.Model):
    code       = models.CharField(max_length=20, unique=True)
    name       = models.CharField(max_length=100)
    phone      = models.CharField(max_length=20, blank=True)
    email      = models.EmailField(blank=True)
    address    = models.TextField(blank=True)
    points     = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self): return f'{self.name} ({self.code})'
    class Meta: ordering=['-created_at']

class Supplier(models.Model):
    code    = models.CharField(max_length=20, unique=True)
    name    = models.CharField(max_length=100)
    phone   = models.CharField(max_length=20, blank=True)
    email   = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self): return f'{self.name} ({self.code})'

class Product(models.Model):
    CAT = [('coffee','Coffee'),('tea','Tea'),('smoothie','Smoothie'),('bakery','Bakery'),('ingredient','วัตถุดิบ')]
    code         = models.CharField(max_length=20, unique=True)
    name         = models.CharField(max_length=100)
    category     = models.CharField(max_length=20, choices=CAT)
    description  = models.TextField(blank=True)
    sale_price   = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    cost_price   = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    stock_qty    = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    min_stock    = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    unit         = models.CharField(max_length=20, default='แก้ว')
    image_url    = models.URLField(blank=True)
    is_available = models.BooleanField(default=True)
    created_at   = models.DateTimeField(auto_now_add=True)
    def __str__(self): return f'{self.code} — {self.name}'
    def is_low(self): return self.stock_qty <= self.min_stock
    def profit(self): return float(self.sale_price) - float(self.cost_price)

class Ingredient(models.Model):
    UNIT = [('g','กรัม'),('kg','กิโลกรัม'),('ml','มล.'),('l','ลิตร'),('pcs','ชิ้น')]
    code          = models.CharField(max_length=20, unique=True)
    name          = models.CharField(max_length=100)
    unit          = models.CharField(max_length=10, choices=UNIT)
    stock_qty     = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    min_stock     = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    cost_per_unit = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    supplier      = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True)
    def __str__(self): return f'{self.name} ({self.stock_qty} {self.unit})'
    def is_low(self): return self.stock_qty <= self.min_stock

class StockMovement(models.Model):
    TYPE = [('in','รับเข้า'),('out','เบิกใช้'),('adjust','ปรับยอด'),('waste','ของเสีย')]
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE, related_name='movements')
    move_type  = models.CharField(max_length=10, choices=TYPE)
    quantity   = models.DecimalField(max_digits=10, decimal_places=2)
    note       = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self): return f'{self.get_move_type_display()} {self.ingredient.name} {self.quantity}'
    class Meta: ordering=['-created_at']

class Employee(models.Model):
    ROLES   = [('barista','Barista'),('cashier','Cashier'),('baker','Baker'),('manager','Manager'),('delivery','Delivery')]
    STATUS  = [('active','ทำงานอยู่'),('leave','ลางาน'),('inactive','ลาออก')]
    code       = models.CharField(max_length=20, unique=True)
    name       = models.CharField(max_length=100)
    role       = models.CharField(max_length=20, choices=ROLES)
    phone      = models.CharField(max_length=20, blank=True)
    email      = models.EmailField(blank=True)
    salary     = models.DecimalField(max_digits=8, decimal_places=0, default=0)
    start_date = models.DateField()
    status     = models.CharField(max_length=20, choices=STATUS, default='active')
    def __str__(self): return f'{self.name} ({self.get_role_display()})'

class SaleOrder(models.Model):
    STATUS = [('draft','แบบร่าง'),('confirmed','ยืนยัน'),('completed','เสร็จสิ้น'),('cancelled','ยกเลิก')]
    TYPES  = [('dine_in','Dine-in'),('pickup','Pickup'),('delivery','Delivery'),('pos','POS')]
    so_number  = models.CharField(max_length=20, unique=True)
    date       = models.DateField(default=timezone.now)
    customer   = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True)
    employee   = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True)
    order_type = models.CharField(max_length=20, choices=TYPES, default='dine_in')
    note       = models.TextField(blank=True)
    discount   = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    subtotal   = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total      = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status     = models.CharField(max_length=20, choices=STATUS, default='confirmed')
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self): return self.so_number
    class Meta: ordering=['-created_at']

class SaleOrderItem(models.Model):
    order    = models.ForeignKey(SaleOrder, on_delete=models.CASCADE, related_name='items')
    product  = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.DecimalField(max_digits=8, decimal_places=2, default=1)
    price    = models.DecimalField(max_digits=8, decimal_places=2)
    discount = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    total    = models.DecimalField(max_digits=10, decimal_places=2, default=0)

class PurchaseOrder(models.Model):
    STATUS = [('draft','แบบร่าง'),('confirmed','ยืนยัน'),('received','รับแล้ว'),('cancelled','ยกเลิก')]
    po_number  = models.CharField(max_length=20, unique=True)
    date       = models.DateField(default=timezone.now)
    supplier   = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True)
    note       = models.TextField(blank=True)
    total      = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status     = models.CharField(max_length=20, choices=STATUS, default='confirmed')
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self): return self.po_number
    class Meta: ordering=['-created_at']

class PurchaseOrderItem(models.Model):
    order      = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='items')
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE)
    quantity   = models.DecimalField(max_digits=8, decimal_places=2, default=1)
    price      = models.DecimalField(max_digits=8, decimal_places=2)
    total      = models.DecimalField(max_digits=10, decimal_places=2, default=0)
