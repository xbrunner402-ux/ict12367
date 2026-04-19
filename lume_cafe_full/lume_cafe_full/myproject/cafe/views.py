from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count
from django.utils import timezone
from django.http import JsonResponse, HttpResponse
from datetime import timedelta, date
import json, csv
from cafe.models import (Customer, Supplier, Product, Ingredient, StockMovement,
                          Employee, SaleOrder, SaleOrderItem, PurchaseOrder, PurchaseOrderItem)

def next_so():
    last = SaleOrder.objects.order_by('-id').first()
    n = (last.pk + 1) if last else 1
    return f'SO-{date.today().strftime("%Y%m")}{n:04d}'

def next_po():
    last = PurchaseOrder.objects.order_by('-id').first()
    n = (last.pk + 1) if last else 1
    return f'PO-{date.today().strftime("%Y%m")}{n:04d}'

def get_low_stock_count():
    return len([i for i in Ingredient.objects.all() if i.is_low()])

# ── LOGIN / LOGOUT ──
def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    error = None
    if request.method == 'POST':
        user = authenticate(request, username=request.POST.get('username'), password=request.POST.get('password'))
        if user:
            login(request, user)
            return redirect(request.GET.get('next', 'dashboard'))
        error = 'ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง'
    return render(request, 'cafe/login.html', {'error': error})

def logout_view(request):
    logout(request)
    return redirect('login')

# ── DASHBOARD ──
@login_required(login_url='login')
def dashboard(request):
    today = timezone.now().date()
    month_start = today.replace(day=1)
    year_start  = today.replace(month=1, day=1)
    rev_today = SaleOrder.objects.filter(date=today, status__in=['confirmed','completed']).aggregate(t=Sum('total'))['t'] or 0
    rev_month = SaleOrder.objects.filter(date__gte=month_start, status__in=['confirmed','completed']).aggregate(t=Sum('total'))['t'] or 0
    rev_year  = SaleOrder.objects.filter(date__gte=year_start, status__in=['confirmed','completed']).aggregate(t=Sum('total'))['t'] or 0
    chart_labels, chart_data = [], []
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        rev = SaleOrder.objects.filter(date=d, status__in=['confirmed','completed']).aggregate(t=Sum('total'))['t'] or 0
        chart_labels.append(d.strftime('%d/%m')); chart_data.append(float(rev))
    top_products = SaleOrderItem.objects.filter(order__date__gte=month_start, order__status__in=['confirmed','completed']
        ).values('product__name').annotate(qty=Sum('quantity'), revenue=Sum('total')).order_by('-revenue')[:5]
    low_ingredients = [i for i in Ingredient.objects.all() if i.is_low()]
    # Donut chart: category breakdown this month
    cat_data = SaleOrderItem.objects.filter(order__date__gte=month_start, order__status__in=['confirmed','completed']
        ).values('product__category').annotate(revenue=Sum('total')).order_by('-revenue')
    cat_labels = [d['product__category'] or 'อื่นๆ' for d in cat_data]
    cat_values = [float(d['revenue']) for d in cat_data]
    return render(request, 'cafe/dashboard.html', {
        'rev_today': rev_today, 'rev_month': rev_month, 'rev_year': rev_year,
        'chart_labels': json.dumps(chart_labels), 'chart_data': json.dumps(chart_data),
        'cat_labels': json.dumps(cat_labels), 'cat_values': json.dumps(cat_values),
        'top_products': top_products, 'recent_sales': SaleOrder.objects.all()[:8],
        'low_ingredients': low_ingredients,
        'pending_so': SaleOrder.objects.filter(status='confirmed').count(),
        'total_customers': Customer.objects.count(),
        'total_products': Product.objects.filter(is_available=True).count(),
        'orders_today': SaleOrder.objects.filter(date=today).count(),
        'low_stock_count': len(low_ingredients),
    })

# ── REPORT ──
@login_required(login_url='login')
def report_sales(request):
    date_from = request.GET.get('from', (date.today() - timedelta(days=30)).strftime('%Y-%m-%d'))
    date_to   = request.GET.get('to', date.today().strftime('%Y-%m-%d'))
    qs = SaleOrder.objects.filter(date__gte=date_from, date__lte=date_to, status__in=['confirmed','completed'])
    total_revenue = qs.aggregate(t=Sum('total'))['t'] or 0
    d_from = date.fromisoformat(date_from); d_to = date.fromisoformat(date_to)
    chart_labels, chart_data = [], []
    for i in range(min((d_to-d_from).days+1, 60)):
        d = d_from + timedelta(days=i)
        rev = qs.filter(date=d).aggregate(t=Sum('total'))['t'] or 0
        chart_labels.append(d.strftime('%d/%m')); chart_data.append(float(rev))
    top_items = SaleOrderItem.objects.filter(order__in=qs).values('product__name','product__code').annotate(qty=Sum('quantity'),revenue=Sum('total')).order_by('-revenue')[:10]
    # CSV export
    if request.GET.get('export') == 'csv':
        response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
        response['Content-Disposition'] = f'attachment; filename="sales_{date_from}_{date_to}.csv"'
        writer = csv.writer(response)
        writer.writerow(['เลขที่','วันที่','ลูกค้า','ประเภท','ยอดรวม','สถานะ'])
        for o in qs:
            writer.writerow([o.so_number, o.date, o.customer.name if o.customer else 'Walk-in',
                             o.get_order_type_display(), float(o.total), o.get_status_display()])
        return response
    return render(request, 'cafe/report_sales.html', {
        'date_from': date_from, 'date_to': date_to,
        'total_revenue': total_revenue, 'total_orders': qs.count(),
        'chart_labels': json.dumps(chart_labels), 'chart_data': json.dumps(chart_data),
        'top_items': top_items, 'orders': qs[:50],
        'low_stock_count': get_low_stock_count(),
    })

# ── POS ──
@login_required(login_url='login')
def pos(request):
    products = Product.objects.filter(is_available=True).order_by('category', 'name')
    employees = Employee.objects.filter(status='active')
    customers = Customer.objects.all()[:50]
    return render(request, 'cafe/pos.html', {
        'products': products, 'employees': employees,
        'customers': customers, 'so_number': next_so(),
        'today': date.today().isoformat(),
    })

def pos_submit(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        items_data = data.get('items', [])
        if not items_data:
            return JsonResponse({'ok': False, 'error': 'ไม่มีรายการ'})
        so_num = next_so()
        customer = Customer.objects.filter(pk=data.get('customer_id')).first() if data.get('customer_id') else None
        employee = Employee.objects.filter(pk=data.get('employee_id')).first() if data.get('employee_id') else None
        discount = float(data.get('discount', 0))
        so = SaleOrder.objects.create(
            so_number=so_num, date=date.today(), customer=customer, employee=employee,
            order_type='pos', note=data.get('note',''), discount=discount, status='confirmed'
        )
        subtotal = 0
        for item in items_data:
            product = Product.objects.get(pk=item['id'])
            qty = float(item['qty']); price = float(item['price'])
            item_total = qty * price
            SaleOrderItem.objects.create(order=so, product=product, quantity=qty, price=price, total=item_total)
            subtotal += item_total
            if product.stock_qty > 0:
                product.stock_qty = max(0, float(product.stock_qty) - qty)
                product.save()
        so.subtotal = subtotal; so.total = subtotal - discount; so.save()
        # Add points to customer (1 point per 10 baht)
        points_earned = 0
        if customer:
            points_earned = int(float(so.total) / 10)
            customer.points += points_earned
            customer.save()
        return JsonResponse({'ok': True, 'so_number': so_num, 'total': float(so.total), 'points_earned': points_earned})
    return JsonResponse({'ok': False})

# ── KDS (Kitchen Display System) ──
@login_required(login_url='login')
def kds(request):
    return render(request, 'cafe/kds.html')

def kds_orders(request):
    orders = SaleOrder.objects.filter(status='confirmed').order_by('created_at')[:20]
    data = []
    for o in orders:
        data.append({
            'pk': o.pk,
            'so_number': o.so_number,
            'created_at': o.created_at.isoformat(),
            'note': o.note,
            'items': [{'name': i.product.name, 'qty': int(i.quantity)} for i in o.items.all()],
        })
    return JsonResponse({'orders': data})

def kds_done(request, pk):
    if request.method == 'POST':
        order = get_object_or_404(SaleOrder, pk=pk)
        order.status = 'completed'
        order.save()
        return JsonResponse({'ok': True})
    return JsonResponse({'ok': False})

# ── SALES ──
@login_required(login_url='login')
def sale_list(request):
    from django.core.paginator import Paginator
    status = request.GET.get('status', '')
    q = request.GET.get('q', '')
    qs = SaleOrder.objects.all()
    if status: qs = qs.filter(status=status)
    if q: qs = qs.filter(so_number__icontains=q) | SaleOrder.objects.filter(customer__name__icontains=q)
    if request.GET.get('export') == 'csv':
        response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
        response['Content-Disposition'] = 'attachment; filename="sales.csv"'
        writer = csv.writer(response)
        writer.writerow(['เลขที่','วันที่','ลูกค้า','ประเภท','ยอดรวม','สถานะ'])
        for o in qs:
            writer.writerow([o.so_number, o.date, o.customer.name if o.customer else 'Walk-in',
                             o.get_order_type_display(), float(o.total), o.get_status_display()])
        return response
    paginator = Paginator(qs, 20)
    page = paginator.get_page(request.GET.get('page', 1))
    return render(request, 'cafe/sale_list.html', {
        'orders': page, 'status': status, 'q': q,
        'page_obj': page, 'low_stock_count': get_low_stock_count()
    })

@login_required(login_url='login')
def sale_new(request):
    if request.method == 'POST':
        so_num = request.POST.get('so_number', next_so())
        cust   = Customer.objects.filter(pk=request.POST.get('customer_id','')).first()
        emp    = Employee.objects.filter(pk=request.POST.get('employee_id','')).first()
        disc   = float(request.POST.get('discount', 0) or 0)
        so = SaleOrder.objects.create(so_number=so_num, date=request.POST.get('date', date.today()),
            customer=cust, employee=emp, order_type=request.POST.get('order_type','dine_in'),
            note=request.POST.get('note',''), discount=disc)
        subtotal = 0
        for pid, qty, price, item_disc in zip(
            request.POST.getlist('product_id'), request.POST.getlist('qty'),
            request.POST.getlist('price'), request.POST.getlist('item_discount')):
            qty=float(qty or 0); price=float(price or 0); item_disc=float(item_disc or 0)
            if qty > 0:
                t = qty*price - item_disc
                SaleOrderItem.objects.create(order=so, product_id=pid, quantity=qty, price=price, discount=item_disc, total=t)
                subtotal += t
        so.subtotal = subtotal; so.total = subtotal - disc; so.save()
        messages.success(request, f'สร้างรายการขาย {so.so_number} สำเร็จ!')
        return redirect('sale_detail', pk=so.pk)
    return render(request, 'cafe/sale_form.html', {
        'so_number': next_so(), 'today': date.today().isoformat(),
        'customers': Customer.objects.all(), 'employees': Employee.objects.filter(status='active'),
        'products': Product.objects.filter(is_available=True),
        'low_stock_count': get_low_stock_count(),
    })

@login_required(login_url='login')
def sale_detail(request, pk):
    return render(request, 'cafe/sale_detail.html', {'order': get_object_or_404(SaleOrder, pk=pk), 'low_stock_count': get_low_stock_count()})

def sale_status(request, pk):
    order = get_object_or_404(SaleOrder, pk=pk)
    if request.method == 'POST':
        order.status = request.POST.get('status', order.status); order.save()
        messages.success(request, 'อัปเดตสถานะแล้ว')
    return redirect('sale_list')

# ── PURCHASE ──
@login_required(login_url='login')
def purchase_list(request):
    status = request.GET.get('status', '')
    qs = PurchaseOrder.objects.all()
    if status: qs = qs.filter(status=status)
    return render(request, 'cafe/purchase_list.html', {'orders': qs, 'status': status, 'low_stock_count': get_low_stock_count()})

@login_required(login_url='login')
def purchase_new(request):
    if request.method == 'POST':
        supp = Supplier.objects.filter(pk=request.POST.get('supplier_id','')).first()
        po = PurchaseOrder.objects.create(po_number=request.POST.get('po_number', next_po()),
            date=request.POST.get('date', date.today()), supplier=supp, note=request.POST.get('note',''))
        total = 0
        for iid, qty, price in zip(request.POST.getlist('ingredient_id'),
                                    request.POST.getlist('qty'), request.POST.getlist('price')):
            qty=float(qty or 0); price=float(price or 0)
            if qty > 0:
                t = qty*price
                PurchaseOrderItem.objects.create(order=po, ingredient_id=iid, quantity=qty, price=price, total=t)
                total += t
        po.total = total; po.save()
        messages.success(request, f'สร้างรายการซื้อ {po.po_number} สำเร็จ!')
        return redirect('purchase_detail', pk=po.pk)
    return render(request, 'cafe/purchase_form.html', {
        'po_number': next_po(), 'today': date.today().isoformat(),
        'suppliers': Supplier.objects.all(), 'ingredients': Ingredient.objects.all(),
        'low_stock_count': get_low_stock_count(),
    })

@login_required(login_url='login')
def purchase_detail(request, pk):
    return render(request, 'cafe/purchase_detail.html', {'order': get_object_or_404(PurchaseOrder, pk=pk), 'low_stock_count': get_low_stock_count()})

def purchase_receive(request, pk):
    order = get_object_or_404(PurchaseOrder, pk=pk)
    if request.method == 'POST':
        for item in order.items.all():
            item.ingredient.stock_qty = float(item.ingredient.stock_qty) + float(item.quantity)
            item.ingredient.save()
            StockMovement.objects.create(ingredient=item.ingredient, move_type='in',
                quantity=item.quantity, note=f'รับจาก {order.po_number}')
        order.status = 'received'; order.save()
        messages.success(request, f'รับสินค้า {order.po_number} เรียบร้อย!')
    return redirect('purchase_list')

# ── PRODUCTS ──
@login_required(login_url='login')
def product_list(request):
    cat = request.GET.get('cat', ''); q = request.GET.get('q', '')
    qs = Product.objects.all()
    if cat: qs = qs.filter(category=cat)
    if q: qs = qs.filter(name__icontains=q)
    return render(request, 'cafe/product_list.html', {'products': qs, 'cat': cat, 'q': q, 'low_stock_count': get_low_stock_count()})

@login_required(login_url='login')
def product_new(request):
    if request.method == 'POST':
        Product.objects.create(code=request.POST['code'], name=request.POST['name'],
            category=request.POST['category'], description=request.POST.get('description',''),
            sale_price=request.POST.get('sale_price',0), cost_price=request.POST.get('cost_price',0),
            stock_qty=request.POST.get('stock_qty',0), min_stock=request.POST.get('min_stock',0),
            unit=request.POST.get('unit','แก้ว'), image_url=request.POST.get('image_url',''),
            is_available=bool(request.POST.get('is_available')))
        messages.success(request, 'เพิ่มสินค้าสำเร็จ!'); return redirect('product_list')
    return render(request, 'cafe/product_form.html', {'action':'new', 'low_stock_count': get_low_stock_count()})

@login_required(login_url='login')
def product_edit(request, pk):
    p = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        for f in ['name','category','description','sale_price','cost_price','stock_qty','min_stock','unit','image_url']:
            setattr(p, f, request.POST.get(f, getattr(p, f)))
        p.is_available = bool(request.POST.get('is_available')); p.save()
        messages.success(request, 'แก้ไขสำเร็จ!'); return redirect('product_list')
    return render(request, 'cafe/product_form.html', {'action':'edit','product':p, 'low_stock_count': get_low_stock_count()})

# ── INGREDIENTS ──
@login_required(login_url='login')
def ingredient_list(request):
    return render(request, 'cafe/ingredient_list.html', {
        'ingredients': Ingredient.objects.all(),
        'movements': StockMovement.objects.all()[:15],
        'low_stock_count': get_low_stock_count(),
    })

@login_required(login_url='login')
def ingredient_new(request):
    if request.method == 'POST':
        last = Ingredient.objects.order_by('-id').first()
        code = f'ING{((last.pk if last else 0)+1):03d}'
        Ingredient.objects.create(code=code, name=request.POST['name'],
            unit=request.POST['unit'], stock_qty=request.POST.get('stock_qty',0),
            min_stock=request.POST.get('min_stock',0), cost_per_unit=request.POST.get('cost_per_unit',0))
        messages.success(request, 'เพิ่มวัตถุดิบสำเร็จ!'); return redirect('ingredient_list')
    return render(request, 'cafe/ingredient_form.html', {'low_stock_count': get_low_stock_count()})

def stock_move(request):
    if request.method == 'POST':
        ing = get_object_or_404(Ingredient, pk=request.POST['ingredient'])
        move_type = request.POST['move_type']
        qty = float(request.POST.get('quantity', 0))
        StockMovement.objects.create(ingredient=ing, move_type=move_type, quantity=qty, note=request.POST.get('note',''))
        if move_type == 'in': ing.stock_qty = float(ing.stock_qty) + qty
        elif move_type in ['out','waste']: ing.stock_qty = max(0, float(ing.stock_qty) - qty)
        else: ing.stock_qty = qty
        ing.save()
        messages.success(request, 'บันทึกสต็อกสำเร็จ!'); return redirect('ingredient_list')
    return redirect('ingredient_list')

# ── CUSTOMERS ──
@login_required(login_url='login')
def customer_list(request):
    q = request.GET.get('q','')
    qs = Customer.objects.all()
    if q: qs = qs.filter(name__icontains=q) | Customer.objects.filter(phone__icontains=q)
    return render(request, 'cafe/customer_list.html', {'customers': qs, 'q': q, 'low_stock_count': get_low_stock_count()})

@login_required(login_url='login')
def customer_new(request):
    if request.method == 'POST':
        last = Customer.objects.order_by('-id').first()
        code = f'C{((last.pk if last else 0)+1):04d}'
        Customer.objects.create(code=code, name=request.POST['name'],
            phone=request.POST.get('phone',''), email=request.POST.get('email',''),
            address=request.POST.get('address',''))
        messages.success(request, 'เพิ่มลูกค้าสำเร็จ!'); return redirect('customer_list')
    return render(request, 'cafe/customer_form.html', {'low_stock_count': get_low_stock_count()})

# ── SUPPLIERS ──
@login_required(login_url='login')
def supplier_list(request):
    return render(request, 'cafe/supplier_list.html', {'suppliers': Supplier.objects.all(), 'low_stock_count': get_low_stock_count()})

@login_required(login_url='login')
def supplier_new(request):
    if request.method == 'POST':
        last = Supplier.objects.order_by('-id').first()
        code = f'SUP{((last.pk if last else 0)+1):03d}'
        Supplier.objects.create(code=code, name=request.POST['name'],
            phone=request.POST.get('phone',''), email=request.POST.get('email',''),
            address=request.POST.get('address',''))
        messages.success(request, 'เพิ่มซัพพลายเออร์สำเร็จ!'); return redirect('supplier_list')
    return render(request, 'cafe/supplier_form.html', {'low_stock_count': get_low_stock_count()})

# ── EMPLOYEES ──
@login_required(login_url='login')
def employee_list(request):
    return render(request, 'cafe/employee_list.html', {'employees': Employee.objects.all(), 'low_stock_count': get_low_stock_count()})

@login_required(login_url='login')
def employee_new(request):
    if request.method == 'POST':
        last = Employee.objects.order_by('-id').first()
        code = f'EMP{((last.pk if last else 0)+1):03d}'
        Employee.objects.create(code=code, name=request.POST['name'], role=request.POST['role'],
            phone=request.POST.get('phone',''), email=request.POST.get('email',''),
            salary=request.POST.get('salary',0), start_date=request.POST['start_date'],
            status=request.POST.get('status','active'))
        messages.success(request, 'เพิ่มพนักงานสำเร็จ!'); return redirect('employee_list')
    return render(request, 'cafe/employee_form.html', {'low_stock_count': get_low_stock_count()})

# ── API ──
def api_products(request):
    products = list(Product.objects.filter(is_available=True).values('id','code','name','sale_price','cost_price','unit','stock_qty','category','image_url'))
    return JsonResponse({'products': products})

def api_ingredients(request):
    ingredients = list(Ingredient.objects.all().values('id','code','name','unit','stock_qty'))
    return JsonResponse({'ingredients': ingredients})


# ── EDIT VIEWS ──
@login_required(login_url='login')
def customer_edit(request, pk):
    c = get_object_or_404(Customer, pk=pk)
    if request.method == 'POST':
        c.name = request.POST.get('name', c.name)
        c.phone = request.POST.get('phone', c.phone)
        c.email = request.POST.get('email', c.email)
        c.address = request.POST.get('address', c.address)
        c.save()
        messages.success(request, f'แก้ไขข้อมูลลูกค้า {c.name} สำเร็จ!')
        return redirect('customer_list')
    return render(request, 'cafe/customer_form.html', {'customer': c, 'action': 'edit', 'low_stock_count': get_low_stock_count()})

@login_required(login_url='login')
def employee_edit(request, pk):
    e = get_object_or_404(Employee, pk=pk)
    if request.method == 'POST':
        for f in ['name','role','phone','email','salary','start_date','status']:
            setattr(e, f, request.POST.get(f, getattr(e, f)))
        e.save()
        messages.success(request, f'แก้ไขข้อมูลพนักงาน {e.name} สำเร็จ!')
        return redirect('employee_list')
    return render(request, 'cafe/employee_form.html', {'employee': e, 'action': 'edit', 'low_stock_count': get_low_stock_count()})

@login_required(login_url='login')
def supplier_edit(request, pk):
    s = get_object_or_404(Supplier, pk=pk)
    if request.method == 'POST':
        s.name = request.POST.get('name', s.name)
        s.phone = request.POST.get('phone', s.phone)
        s.email = request.POST.get('email', s.email)
        s.address = request.POST.get('address', s.address)
        s.save()
        messages.success(request, f'แก้ไขข้อมูลซัพพลายเออร์ {s.name} สำเร็จ!')
        return redirect('supplier_list')
    return render(request, 'cafe/supplier_form.html', {'supplier': s, 'action': 'edit', 'low_stock_count': get_low_stock_count()})

@login_required(login_url='login')
def ingredient_edit(request, pk):
    i = get_object_or_404(Ingredient, pk=pk)
    if request.method == 'POST':
        i.name = request.POST.get('name', i.name)
        i.unit = request.POST.get('unit', i.unit)
        i.stock_qty = request.POST.get('stock_qty', i.stock_qty)
        i.min_stock = request.POST.get('min_stock', i.min_stock)
        i.cost_per_unit = request.POST.get('cost_per_unit', i.cost_per_unit)
        i.save()
        messages.success(request, f'แก้ไขข้อมูลวัตถุดิบ {i.name} สำเร็จ!')
        return redirect('ingredient_list')
    return render(request, 'cafe/ingredient_form.html', {'ingredient': i, 'action': 'edit', 'low_stock_count': get_low_stock_count()})

# ── PROFIT REPORT ──
@login_required(login_url='login')
def report_profit(request):
    from datetime import date
    date_from = request.GET.get('from', (date.today().replace(day=1)).strftime('%Y-%m-%d'))
    date_to = request.GET.get('to', date.today().strftime('%Y-%m-%d'))
    qs = SaleOrder.objects.filter(date__gte=date_from, date__lte=date_to, status__in=['confirmed','completed'])
    items = SaleOrderItem.objects.filter(order__in=qs)
    total_revenue = qs.aggregate(t=Sum('total'))['t'] or 0
    total_cost = sum(float(i.quantity) * float(i.product.cost_price) for i in items)
    total_profit = float(total_revenue) - total_cost
    margin = (total_profit / float(total_revenue) * 100) if total_revenue else 0
    # By product
    product_profit = {}
    for i in items:
        pid = i.product.pk
        if pid not in product_profit:
            product_profit[pid] = {'name': i.product.name, 'qty': 0, 'revenue': 0, 'cost': 0}
        product_profit[pid]['qty'] += float(i.quantity)
        product_profit[pid]['revenue'] += float(i.total)
        product_profit[pid]['cost'] += float(i.quantity) * float(i.product.cost_price)
    for p in product_profit.values():
        p['profit'] = p['revenue'] - p['cost']
        p['margin'] = (p['profit'] / p['revenue'] * 100) if p['revenue'] else 0
    products_sorted = sorted(product_profit.values(), key=lambda x: x['profit'], reverse=True)
    if request.GET.get('export') == 'csv':
        import csv
        from django.http import HttpResponse
        response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
        response['Content-Disposition'] = f'attachment; filename="profit_{date_from}_{date_to}.csv"'
        writer = csv.writer(response)
        writer.writerow(['สินค้า','จำนวน','รายรับ','ต้นทุน','กำไร','มาร์จิน%'])
        for p in products_sorted:
            writer.writerow([p['name'], p['qty'], f"{p['revenue']:.2f}", f"{p['cost']:.2f}", f"{p['profit']:.2f}", f"{p['margin']:.1f}"])
        return response
    return render(request, 'cafe/report_profit.html', {
        'date_from': date_from, 'date_to': date_to,
        'total_revenue': total_revenue, 'total_cost': total_cost,
        'total_profit': total_profit, 'margin': margin,
        'products': products_sorted, 'total_orders': qs.count(),
        'low_stock_count': get_low_stock_count(),
    })

# ── SETTINGS ──
@login_required(login_url='login')
def settings_view(request):
    from django.conf import settings as django_settings
    import json, os
    settings_file = os.path.join(django_settings.BASE_DIR, 'cafe_settings.json')
    defaults = {'shop_name': 'Lumè Café', 'shop_address': '123 ถ.เจริญกรุง เขตบางรัก กรุงเทพฯ 10500',
                'shop_phone': '02-XXX-XXXX', 'shop_hours': '08:00 – 20:00 น.', 'shop_website': 'www.lumecafe.th',
                'delete_password': '1234', 'points_per_baht': 10, 'points_per_discount_baht': 200, 'points_discount_value': 50}
    if os.path.exists(settings_file):
        try:
            with open(settings_file, encoding='utf-8') as f:
                shop_settings = {**defaults, **json.load(f)}
        except (UnicodeDecodeError, json.JSONDecodeError):
            # File corrupted or wrong encoding - reset to defaults
            shop_settings = defaults
            with open(settings_file, 'w', encoding='utf-8') as f:
                json.dump(shop_settings, f, ensure_ascii=False, indent=2)
    else:
        shop_settings = defaults
    if request.method == 'POST':
        for key in defaults:
            if key in request.POST:
                shop_settings[key] = request.POST[key]
        with open(settings_file, 'w', encoding='utf-8') as f:
            json.dump(shop_settings, f, ensure_ascii=False, indent=2)
        messages.success(request, 'บันทึกการตั้งค่าสำเร็จ!')
        return redirect('settings')
    return render(request, 'cafe/settings.html', {'s': shop_settings, 'low_stock_count': get_low_stock_count()})


# ── DELETE ──
DELETE_PASSWORD = '1234'

def check_delete_password(request):
    return request.POST.get('delete_password', '') == DELETE_PASSWORD

def sale_delete(request, pk):
    order = get_object_or_404(SaleOrder, pk=pk)
    if request.method == 'POST':
        if not check_delete_password(request):
            messages.error(request, '❌ รหัสผ่านไม่ถูกต้อง'); return redirect('sale_list')
        order.delete(); messages.success(request, f'ลบรายการขาย {order.so_number} แล้ว')
    return redirect('sale_list')

def purchase_delete(request, pk):
    order = get_object_or_404(PurchaseOrder, pk=pk)
    if request.method == 'POST':
        if not check_delete_password(request):
            messages.error(request, '❌ รหัสผ่านไม่ถูกต้อง'); return redirect('purchase_list')
        order.delete(); messages.success(request, f'ลบรายการซื้อ {order.po_number} แล้ว')
    return redirect('purchase_list')

def product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        if not check_delete_password(request):
            messages.error(request, '❌ รหัสผ่านไม่ถูกต้อง'); return redirect('product_list')
        name = product.name; product.delete(); messages.success(request, f'ลบสินค้า "{name}" แล้ว')
    return redirect('product_list')

def ingredient_delete(request, pk):
    ing = get_object_or_404(Ingredient, pk=pk)
    if request.method == 'POST':
        if not check_delete_password(request):
            messages.error(request, '❌ รหัสผ่านไม่ถูกต้อง'); return redirect('ingredient_list')
        name = ing.name; ing.delete(); messages.success(request, f'ลบวัตถุดิบ "{name}" แล้ว')
    return redirect('ingredient_list')

def customer_delete(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    if request.method == 'POST':
        if not check_delete_password(request):
            messages.error(request, '❌ รหัสผ่านไม่ถูกต้อง'); return redirect('customer_list')
        name = customer.name; customer.delete(); messages.success(request, f'ลบลูกค้า "{name}" แล้ว')
    return redirect('customer_list')

def supplier_delete(request, pk):
    supplier = get_object_or_404(Supplier, pk=pk)
    if request.method == 'POST':
        if not check_delete_password(request):
            messages.error(request, '❌ รหัสผ่านไม่ถูกต้อง'); return redirect('supplier_list')
        name = supplier.name; supplier.delete(); messages.success(request, f'ลบซัพพลายเออร์ "{name}" แล้ว')
    return redirect('supplier_list')

def employee_delete(request, pk):
    emp = get_object_or_404(Employee, pk=pk)
    if request.method == 'POST':
        if not check_delete_password(request):
            messages.error(request, '❌ รหัสผ่านไม่ถูกต้อง'); return redirect('employee_list')
        name = emp.name; emp.delete(); messages.success(request, f'ลบพนักงาน "{name}" แล้ว')
    return redirect('employee_list')
