from django.contrib.auth.models import AbstractUser
from django.db import models
from datetime import timedelta
from django.utils import timezone

class User(AbstractUser):

    ROLE_CHOICES = (
        ("admin", "Admin"),
        ("user", "User"),
        ("farmer", "Farmer"),
        ("vendor","Vendor"),
        ("delivery", "Delivery Boy"),
        ("collection_center", "Collection Center"),
    )

    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    country_code = models.CharField(max_length=5, default="+91") 
    phone = models.CharField(max_length=15, unique=True, null=True, blank=True)
    profile_image = models.ImageField(
    upload_to='profile_images/',
    null=True,
    blank=True
)
    is_verified = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.username 

def otp_expiry():
    return timezone.now() + timedelta(seconds=59)
class OTP(models.Model):

    user = models.ForeignKey(
        "core_app.User",
        on_delete=models.CASCADE,
        related_name="user_otps",
        default=False
    )

    otp = models.CharField(max_length=6)

    created_at = models.DateTimeField(auto_now_add=True)

    expire_at = models.DateTimeField(default=otp_expiry)

    def is_expired(self):
        return timezone.now() > self.expire_at

    def __str__(self):
        return f"{self.user.phone} - {self.otp}"     
    
class State(models.Model):

    name = models.CharField(max_length=100)
    state_code = models.CharField(max_length=10, unique=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "states"
        ordering = ["name"]

    def __str__(self):
        return self.name


class City(models.Model):

    state = models.ForeignKey(
        State,
        on_delete=models.CASCADE,
        related_name="cities"
    )

    name = models.CharField(max_length=100)
    pincode = models.CharField(max_length=10, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "cities"
        ordering = ["name"]

    def __str__(self):
        return self.name    



class Address(models.Model):

    user = models.ForeignKey("core_app.User", on_delete=models.CASCADE, related_name='user_address')
    address_line = models.TextField()
    city = models.ForeignKey(
        City,
        on_delete=models.CASCADE,
        related_name="addresses"
    )

    state = models.ForeignKey(
        State,
        on_delete=models.CASCADE,
        related_name="addresses"
    )

    pincode = models.CharField(max_length=10)

    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)

    created_at = models.DateTimeField(auto_now_add=True)  

    def __str__(self):
        return self.user.username    


class Seller(models.Model):
    SELLER_TYPE = (
        ("farmer", "Farmer"),
        ("vendor", "Vendor"),
    )
    user = models.OneToOneField("core_app.User", on_delete=models.CASCADE)
    seller_type = models.CharField(max_length=20, choices=SELLER_TYPE, default='farmer')


    farm_name = models.CharField(max_length=200)
    farm_location = models.CharField(max_length=200)

    bank_account = models.CharField(max_length=50)
    ifsc_code = models.CharField(max_length=20)

    is_verified = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.farm_name


class CollectionCenter(models.Model):
    user = models.OneToOneField("core_app.User", on_delete=models.CASCADE)

    center_name = models.CharField(max_length=200)
    address = models.TextField(blank=True, null=True,default=False)
    city = models.CharField(max_length=100,blank=True, null=True)
    state = models.CharField(max_length=100,blank=True, null=True)   
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True) 

    is_verified = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.center_name
    
class CollectionOrder(models.Model):

    order = models.ForeignKey("core_order.Order", on_delete=models.CASCADE)

    collection_center = models.ForeignKey(
        "core_app.CollectionCenter",
        on_delete=models.CASCADE
    )

    status = models.CharField(
        max_length=20,
        choices=(
            ("pending", "Pending"),
            ("ready", "Ready"),
            ("assigned", "Assigned to Delivery"),
        )
    )

    created_at = models.DateTimeField(auto_now_add=True)

class VendorOrder(models.Model):

    order = models.OneToOneField("core_order.Order", on_delete=models.CASCADE)

    vendor = models.ForeignKey("core_app.Seller", on_delete=models.CASCADE)

    status = models.CharField(
        max_length=20,
        choices=(
            ("assigned", "Assigned"),
            ("accepted", "Accepted"),
            ("packed", "Packed"),
            ("ready", "Ready"),
        )
    )        
    

class Subscription(models.Model):

    user = models.ForeignKey("core_app.User", on_delete=models.CASCADE)

    product = models.ForeignKey("core_product.Product", on_delete=models.CASCADE)

    quantity = models.IntegerField()

    start_date = models.DateField()
    end_date = models.DateField()

    is_active = models.BooleanField(default=True)