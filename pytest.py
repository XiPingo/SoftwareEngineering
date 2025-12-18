# test_secondhand.py
import os
import tempfile
import unittest
from dataclasses import asdict

# 假定 secondhand.py 在同目录下
import main

class SecondhandUnitIntegrationTests(unittest.TestCase):
    def setUp(self):
        # 每个测试使用独立临时目录，避免污染真实文件
        self.tmpdir = tempfile.TemporaryDirectory()
        self.orig_cwd = os.getcwd()
        os.chdir(self.tmpdir.name)
        # ensure images dir exists (module constant)
        os.makedirs(main.IMAGES_DIR, exist_ok=True)

    def tearDown(self):
        os.chdir(self.orig_cwd)
        self.tmpdir.cleanup()

    # 单元测试：基础工具函数
    def test_ensure_int_id_empty(self):
        self.assertEqual(main.ensure_int_id([]), 1)

    def test_ensure_int_id_nonempty(self):
        self.assertEqual(main.ensure_int_id([1,2,5]), 6)

    def test_safe_float_valid(self):
        self.assertEqual(main.safe_float("3.14"), 3.14)

    def test_safe_float_invalid(self):
        self.assertEqual(main.safe_float("abc", default=7.7), 7.7)

    # 单元测试：数据对象方法
    def test_user_update_profile(self):
        u = main.User(1, "a@b", "123", "pw", "nick")
        u.updateProfile("x@x","999","nn","/path/a.png")
        self.assertEqual(u.email, "x@x")
        self.assertEqual(u.avatar, "/path/a.png")

    def test_product_edit(self):
        p = main.Product(1, "old", "cat", "desc", 1.0, [], 2)
        p.edit("new","c2","desc2", 9.9, ["i1","i2"])
        self.assertEqual(p.name, "new")
        self.assertEqual(p.price, 9.9)
        self.assertEqual(p.images, ["i1","i2"])

    # 单元测试：copy_image_to_storage - failure & success
    def test_copy_image_to_storage_nonexistent(self):
        self.assertIsNone(main.copy_image_to_storage("no_such_file.jpg"))

    def test_copy_image_to_storage_success(self):
        # create a dummy file (not necessarily an image) - function only copies the file
        src = os.path.join(os.getcwd(), "dummy.txt")
        with open(src, "w", encoding="utf-8") as f:
            f.write("hello")
        dst = main.copy_image_to_storage(src)
        self.assertIsNotNone(dst)
        self.assertTrue(os.path.exists(dst))

    # Storage 持久化（单元/集成）
    def test_storage_admin_created_and_persistence(self):
        users_file = "u.json"
        products_file = "p.json"
        # ensure no preexisting files
        if os.path.exists(users_file): os.remove(users_file)
        s = main.Storage(users_file=users_file, products_file=products_file)
        # admin 自动创建
        self.assertTrue(any(u.is_admin for u in s.users))
        # add a user and a product then save & reload
        u = main.User(999, "u@x", "", "p","u")
        s.users.append(u)
        p = main.Product(50, "prod", "cat", "d", 1.2, [], sellerId=999)
        s.products.append(p)
        s.save_users(); s.save_products()
        s2 = main.Storage(users_file=users_file, products_file=products_file)
        self.assertTrue(any(u.userId == 999 for u in s2.users))
        self.assertTrue(any(p.productId == 50 for p in s2.products))

    # 集成测试 1：删除用户 -> 其商品被删除
    def test_integration_delete_user_removes_products_and_save(self):
        users_file = "ux.json"; products_file = "px.json"
        s = main.Storage(users_file=users_file, products_file=products_file)
        u = main.User(10, "a@b","", "pw","A")
        s.users.append(u)
        p1 = main.Product(101, "p1","c","d", 2.0, [], sellerId=10)
        p2 = main.Product(102, "p2","c","d", 3.0, [], sellerId=11)
        s.products.extend([p1,p2])
        s.save_users(); s.save_products()
        # simulate admin deletion logic
        s.products = [p for p in s.products if p.sellerId != 10]
        s.users = [user for user in s.users if user.userId != 10]
        s.save_products(); s.save_users()
        s3 = main.Storage(users_file=users_file, products_file=products_file)
        self.assertFalse(any(u.userId == 10 for u in s3.users))
        self.assertFalse(any(p.sellerId == 10 for p in s3.products))

    # 集成测试 2：删除商品 -> 从 favorites 中移除
    def test_integration_delete_product_removes_from_favorites(self):
        users_file = "uf.json"; products_file = "pf.json"
        s = main.Storage(users_file=users_file, products_file=products_file)
        u = main.User(20, "x@x","", "pw","X", favorites=[201])
        s.users.append(u)
        p = main.Product(201, "px","c","d", 1.0, [], sellerId=20)
        s.products.append(p)
        s.save_products(); s.save_users()
        # admin deletes product 201
        s.products = [pp for pp in s.products if pp.productId != 201]
        for uu in s.users:
            if 201 in uu.favorites:
                uu.favorites.remove(201)
        s.save_products(); s.save_users()
        s2 = main.Storage(users_file=users_file, products_file=products_file)
        self.assertFalse(any(p.productId == 201 for p in s2.products))
        self.assertFalse(any(201 in u.favorites for u in s2.users))


if __name__ == "__main__":
    unittest.main()
