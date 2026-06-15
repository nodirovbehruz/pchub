import os
import django
import sys
import unittest
from django.test import Client, TestCase

# Mock Django setup
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings.settings")
django.setup()
from django.conf import settings
settings.ALLOWED_HOSTS.append("testserver")

from django.contrib.auth import get_user_model
from django.urls import reverse

User = get_user_model()

class SenetUIQA(TestCase):
    def setUp(self):
        # Create a test client
        self.client = Client()
        # Create a superuser to access the admin interfaces
        self.username = "senet_qa_admin"
        self.password = "senet12345"
        self.user = User.objects.create_superuser(
            username=self.username, email="qa@pchub.com", password=self.password
        )
        # Login
        self.client.login(username=self.username, password=self.password)

    def test_sidebar_presence_on_admin_index(self):
        print("\n[QA] Testing Admin Index & Sidebar...")
        response = self.client.get("/admin/")
        self.assertEqual(response.status_code, 200, "Admin index should return 200")
        
        # Verify custom SPA layout
        content = response.content.decode('utf-8')
        if "id=\"senet-sidebar\"" in content:
            print("✅ SENET Sidebar successfully injected into the global layout.")
        else:
            self.fail("SENET Sidebar not found on the page!")
            
        if "hotwired/turbo" in content:
            print("✅ Hotwire Turbo (SPA Routing) is active.")

    def test_cash_register_zreport(self):
        print("\n[QA] Testing Cash Register (Z-Reports) Interface...")
        response = self.client.get("/admin/billing/shift/dashboard/")
        self.assertEqual(response.status_code, 200, "Cash Register should return 200")
        
        content = response.content.decode('utf-8')
        if "Управление Кассой" in content:
            print("✅ The Cash Register UI rendered correctly.")
        else:
            self.fail("Cash Register header missing.")

    def test_shop_pos(self):
        print("\n[QA] Testing Shop Point-of-Sale (POS) Interface...")
        response = self.client.get("/admin/shops/product/pos/")
        self.assertEqual(response.status_code, 200, "Shop POS should return 200")
        
        content = response.content.decode('utf-8')
        if "id=\"cart-items\"" in content:
            print("✅ The Shop POS and Cart UI rendered correctly.")
        else:
            self.fail("Shop Cart container missing.")

if __name__ == "__main__":
    print("="*60)
    print("🚀 PCHUB PRO (SENET CLONE) - AUTOMATED UI QA PIPELINE")
    print("="*60)
    # Run tests programmatically
    unittest.main(verbosity=2)
