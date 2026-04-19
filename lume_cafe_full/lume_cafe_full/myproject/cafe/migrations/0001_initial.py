from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone

class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel('Customer', fields=[
            ('id', models.BigAutoField(primary_key=True, serialize=False)),
            ('code', models.CharField(max_length=20, unique=True)),
            ('name', models.CharField(max_length=100)),
            ('phone', models.CharField(blank=True, max_length=20)),
            ('email', models.EmailField(blank=True)),
            ('address', models.TextField(blank=True)),
            ('points', models.PositiveIntegerField(default=0)),
            ('created_at', models.DateTimeField(auto_now_add=True)),
        ], options={'ordering': ['-created_at']}),

        migrations.CreateModel('Supplier', fields=[
            ('id', models.BigAutoField(primary_key=True, serialize=False)),
            ('code', models.CharField(max_length=20, unique=True)),
            ('name', models.CharField(max_length=100)),
            ('phone', models.CharField(blank=True, max_length=20)),
            ('email', models.EmailField(blank=True)),
            ('address', models.TextField(blank=True)),
            ('created_at', models.DateTimeField(auto_now_add=True)),
        ]),

        migrations.CreateModel('Product', fields=[
            ('id', models.BigAutoField(primary_key=True, serialize=False)),
            ('code', models.CharField(max_length=20, unique=True)),
            ('name', models.CharField(max_length=100)),
            ('category', models.CharField(max_length=20, choices=[
                ('coffee','Coffee'),('tea','Tea'),('smoothie','Smoothie'),
                ('bakery','Bakery'),('ingredient','วัตถุดิบ')])),
            ('description', models.TextField(blank=True)),
            ('sale_price', models.DecimalField(decimal_places=2, default=0, max_digits=8)),
            ('cost_price', models.DecimalField(decimal_places=2, default=0, max_digits=8)),
            ('stock_qty', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
            ('min_stock', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
            ('unit', models.CharField(default='แก้ว', max_length=20)),
            ('image_url', models.URLField(blank=True)),
            ('is_available', models.BooleanField(default=True)),
            ('created_at', models.DateTimeField(auto_now_add=True)),
        ]),

        migrations.CreateModel('Ingredient', fields=[
            ('id', models.BigAutoField(primary_key=True, serialize=False)),
            ('code', models.CharField(max_length=20, unique=True)),
            ('name', models.CharField(max_length=100)),
            ('unit', models.CharField(max_length=10, choices=[
                ('g','กรัม'),('kg','กิโลกรัม'),('ml','มล.'),('l','ลิตร'),('pcs','ชิ้น')])),
            ('stock_qty', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
            ('min_stock', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
            ('cost_per_unit', models.DecimalField(decimal_places=2, default=0, max_digits=8)),
            ('supplier', models.ForeignKey(blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL, to='cafe.supplier')),
        ]),

        migrations.CreateModel('Employee', fields=[
            ('id', models.BigAutoField(primary_key=True, serialize=False)),
            ('code', models.CharField(max_length=20, unique=True)),
            ('name', models.CharField(max_length=100)),
            ('role', models.CharField(max_length=20, choices=[
                ('barista','Barista'),('cashier','Cashier'),('baker','Baker'),
                ('manager','Manager'),('delivery','Delivery')])),
            ('phone', models.CharField(blank=True, max_length=20)),
            ('email', models.EmailField(blank=True)),
            ('salary', models.DecimalField(decimal_places=0, default=0, max_digits=8)),
            ('start_date', models.DateField()),
            ('status', models.CharField(default='active', max_length=20)),
        ]),

        migrations.CreateModel('StockMovement', fields=[
            ('id', models.BigAutoField(primary_key=True, serialize=False)),
            ('move_type', models.CharField(max_length=10, choices=[
                ('in','รับเข้า'),('out','เบิกใช้'),('adjust','ปรับยอด'),('waste','ของเสีย')])),
            ('quantity', models.DecimalField(decimal_places=2, max_digits=10)),
            ('note', models.TextField(blank=True)),
            ('created_at', models.DateTimeField(auto_now_add=True)),
            ('ingredient', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                related_name='movements', to='cafe.ingredient')),
        ], options={'ordering': ['-created_at']}),

        migrations.CreateModel('SaleOrder', fields=[
            ('id', models.BigAutoField(primary_key=True, serialize=False)),
            ('so_number', models.CharField(max_length=20, unique=True)),
            ('date', models.DateField(default=django.utils.timezone.now)),
            ('order_type', models.CharField(default='dine_in', max_length=20)),
            ('note', models.TextField(blank=True)),
            ('discount', models.DecimalField(decimal_places=2, default=0, max_digits=8)),
            ('subtotal', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
            ('total', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
            ('status', models.CharField(default='confirmed', max_length=20)),
            ('created_at', models.DateTimeField(auto_now_add=True)),
            ('customer', models.ForeignKey(blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL, to='cafe.customer')),
            ('employee', models.ForeignKey(blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL, to='cafe.employee')),
        ], options={'ordering': ['-created_at']}),

        migrations.CreateModel('SaleOrderItem', fields=[
            ('id', models.BigAutoField(primary_key=True, serialize=False)),
            ('quantity', models.DecimalField(decimal_places=2, default=1, max_digits=8)),
            ('price', models.DecimalField(decimal_places=2, max_digits=8)),
            ('discount', models.DecimalField(decimal_places=2, default=0, max_digits=8)),
            ('total', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
            ('order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                related_name='items', to='cafe.saleorder')),
            ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                to='cafe.product')),
        ]),

        migrations.CreateModel('PurchaseOrder', fields=[
            ('id', models.BigAutoField(primary_key=True, serialize=False)),
            ('po_number', models.CharField(max_length=20, unique=True)),
            ('date', models.DateField(default=django.utils.timezone.now)),
            ('note', models.TextField(blank=True)),
            ('total', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
            ('status', models.CharField(default='confirmed', max_length=20)),
            ('created_at', models.DateTimeField(auto_now_add=True)),
            ('supplier', models.ForeignKey(blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL, to='cafe.supplier')),
        ], options={'ordering': ['-created_at']}),

        migrations.CreateModel('PurchaseOrderItem', fields=[
            ('id', models.BigAutoField(primary_key=True, serialize=False)),
            ('quantity', models.DecimalField(decimal_places=2, default=1, max_digits=8)),
            ('price', models.DecimalField(decimal_places=2, max_digits=8)),
            ('total', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
            ('order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                related_name='items', to='cafe.purchaseorder')),
            ('ingredient', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                to='cafe.ingredient')),
        ]),
    ]
