from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):

    ROLE_CHOICES = (
        ("admin", "Admin"),
        ("user", "User"),
        ("farmer", "Farmer"),
        ("vendor","Vendor"),
        ("delivery", "Delivery Boy"),
    )

    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    phone = models.CharField(max_length=15, unique=True, null=True, blank=True)
    is_verified = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.username 
    
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
