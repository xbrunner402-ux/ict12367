from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from myapp.models import Person

# ฟังก์ชันหน้าหลัก (ดึงข้อมูลมาแสดงตาราง)
def index(request):
    # 1. ดึงข้อมูลประชากรทั้งหมดมาก่อน
    all_person = Person.objects.all()
    
    # 2. รับค่าคำค้นหาจากช่องค้นหา (name="q")
    query = request.GET.get('q')
    
    # 3. ตรวจสอบว่ามีคำค้นหาถูกพิมพ์ส่งมาหรือไม่
    if query:
        # ถ้ามีคำค้นหา ให้กรองข้อมูลเฉพาะคนที่ชื่อ (name) หรืออายุ (age) ตรงกับคำค้นหา
        all_person = all_person.filter(Q(name__icontains=query) | Q(age__icontains=query))
        
    # 4. ส่งข้อมูลไปแสดงผลที่ template
    return render(request, "index.html", {"all_person": all_person})

# ฟังก์ชันหน้าฟอร์ม (รับข้อมูลและบันทึก)
def form(request):
    if request.method == "POST":
        # รับข้อมูลจากฟอร์ม
        name = request.POST.get("name")
        age = request.POST.get("age")
        
        # บันทึกข้อมูลลงฐานข้อมูล
        person = Person.objects.create(
            name=name,
            age=age
        )
        # เปลี่ยนเส้นทางไปหน้าแรก
        return redirect("/")
    else:
        # แสดงฟอร์ม
        return render(request, "form.html")
    # (โค้ดด้านบนมีฟังก์ชัน index และ form อยู่แล้ว ไม่ต้องลบทิ้งนะครับ)

# --- เพิ่มฟังก์ชันนี้ต่อท้าย ---

# ฟังก์ชันสำหรับการแก้ไขข้อมูล
def edit(request, person_id):
    # ดึงข้อมูลประชากรตาม ID ที่ส่งมา
    person = get_object_or_404(Person, pk=person_id)
    
    if request.method == "POST":
        # รับข้อมูลที่ถูกแก้ไขจากฟอร์ม
        name = request.POST.get("name")
        age = request.POST.get("age")
        
        # บันทึกข้อมูลที่แก้ไขแล้วลงฐานข้อมูล
        person.name = name
        person.age = age
        person.save()
        
        # เปลี่ยนเส้นทางไปหน้าแรก
        return redirect("/")
    else:
        # แสดงฟอร์มแก้ไขข้อมูล พร้อมส่งข้อมูลเดิมไปโชว์ในช่องกรอก
        return render(request, "edit.html", {"person": person})

# ฟังก์ชันสำหรับการลบข้อมูล
def delete(request, person_id):
    # ดึงข้อมูลประชากรตาม ID ที่ส่งมา
    person = get_object_or_404(Person, pk=person_id)
    # สั่งลบข้อมูล
    person.delete()
    # เปลี่ยนเส้นทางกลับไปหน้าแรก
    return redirect("/")