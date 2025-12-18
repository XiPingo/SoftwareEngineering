# -*- coding: utf-8 -*-
"""
Second-hand Platform - Enhanced Tkinter GUI (single-file)

Features:
- User register/login (JSON persistence in users.json)
- Product publish / edit / delete (JSON persistence in products.json)
- Product browse / search / details with image thumbnail (images/ folder)
- Image handling via Pillow (supports JPG/PNG/GIF)
- Product comments (留言) per product
- Favorites (收藏) stored per user
- Admin panel: view/delete users, view/delete products
"""

import os
import json
import shutil
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from dataclasses import dataclass, asdict, field
from typing import List, Optional, Dict
from PIL import Image, ImageTk

# ---------------------------
# Constants / Helpers
# ---------------------------
USERS_FILE = "users.json"
PRODUCTS_FILE = "products.json"
IMAGES_DIR = "images"

os.makedirs(IMAGES_DIR, exist_ok=True)


def ensure_int_id(existing_ids: List[int]) -> int:
    return (max(existing_ids) + 1) if existing_ids else 1


def safe_float(v, default=0.0):
    try:
        return float(v)
    except Exception:
        return default


# ---------------------------
# Data Models
# ---------------------------
@dataclass
class User:
    userId: int
    email: str
    phone: str
    password: str
    nickname: str
    avatar: str = ""
    is_admin: bool = False
    favorites: List[int] = field(default_factory=list)  # list of productIds

    def updateProfile(self, email, phone, nickname, avatar):
        self.email = email
        self.phone = phone
        self.nickname = nickname
        self.avatar = avatar


@dataclass
class Product:
    productId: int
    name: str
    category: str
    description: str
    price: float
    images: List[str]
    sellerId: int
    comments: List[Dict] = field(default_factory=list)  # each comment: {'userId', 'nickname', 'text'}

    def edit(self, name, category, description, price, images):
        self.name = name
        self.category = category
        self.description = description
        self.price = price
        self.images = images


# ---------------------------
# Storage
# ---------------------------
class Storage:
    def __init__(self, users_file=USERS_FILE, products_file=PRODUCTS_FILE):
        self.users_file = users_file
        self.products_file = products_file
        self.users: List[User] = self.load_users()
        self.products: List[Product] = self.load_products()
        # Ensure admin exists
        if not any(u.is_admin for u in self.users):
            # create default admin
            admin_id = ensure_int_id([u.userId for u in self.users])
            admin = User(admin_id, "admin@example.com", "", "admin", "Administrator", "", True, [])
            self.users.append(admin)
            self.save_users()

    def load_users(self) -> List[User]:
        if not os.path.exists(self.users_file):
            return []
        with open(self.users_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            return [User(**u) for u in data]

    def save_users(self):
        with open(self.users_file, "w", encoding="utf-8") as f:
            json.dump([asdict(u) for u in self.users], f, ensure_ascii=False, indent=2)

    def load_products(self) -> List[Product]:
        if not os.path.exists(self.products_file):
            return []
        with open(self.products_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            return [Product(**p) for p in data]

    def save_products(self):
        with open(self.products_file, "w", encoding="utf-8") as f:
            json.dump([asdict(p) for p in self.products], f, ensure_ascii=False, indent=2)


# ---------------------------
# Image utilities
# ---------------------------
def copy_image_to_storage(src_path: str) -> Optional[str]:
    """
    Copy image to IMAGES_DIR and return relative path (images/...)
    If fails, return None.
    """
    try:
        if not src_path:
            return None
        if not os.path.exists(src_path):
            return None
        basename = os.path.basename(src_path)
        # avoid overwrite: append numeric suffix if needed
        name, ext = os.path.splitext(basename)
        candidate = basename
        i = 1
        while os.path.exists(os.path.join(IMAGES_DIR, candidate)):
            candidate = f"{name}_{i}{ext}"
            i += 1
        dst = os.path.join(IMAGES_DIR, candidate)
        shutil.copy2(src_path, dst)
        return os.path.join(IMAGES_DIR, candidate).replace("\\", "/")
    except Exception as e:
        print("copy image failed:", e)
        return None


def load_image_for_ui(path: str, size=(160, 160)):
    """Return PhotoImage or None. Caller must keep reference."""
    try:
        if not path or not os.path.exists(path):
            return None
        img = Image.open(path)
        img.thumbnail(size)  # preserve aspect ratio
        return ImageTk.PhotoImage(img)
    except Exception as e:
        # print("load image error:", e)
        return None


# ---------------------------
# Application
# ---------------------------
class SecondHandApp:
    def __init__(self, width=1000, height=650):
        self._search_results = None
        self.storage = Storage()
        self.current_user: Optional[User] = None
        self.root = tk.Tk()
        self.root.title("Second-hand Platform")
        self.root.geometry(f"{width}x{height}")
        self.image_cache = {}  # keep PhotoImage references: key -> PhotoImage
        self._setup_style()
        self._build_layout()

    # ----- Styling -----
    def _setup_style(self):
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure("TFrame", background="#f6f7fb")
        style.configure("Header.TLabel", font=("Helvetica", 18, "bold"), background="#2d3447", foreground="white",
                        padding=8)
        style.configure("Title.TLabel", font=("Helvetica", 14, "bold"))
        style.configure("Card.TFrame", background="white", relief="flat")
        style.configure("TButton", padding=6)

    # ----- Layout -----
    def _build_layout(self):
        self.header = ttk.Frame(self.root)
        self.header.pack(side=tk.TOP, fill=tk.X)
        header_label = ttk.Label(self.header, text="二手商品平台", style="Header.TLabel")
        header_label.pack(fill=tk.X)

        self.body = ttk.Frame(self.root)
        self.body.pack(fill=tk.BOTH, expand=True)

        self.sidebar = ttk.Frame(self.body, width=220)
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y)
        self._build_sidebar()

        self.main = ttk.Frame(self.body)
        self.main.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._show_welcome()

    def _clear_main(self):
        for w in self.main.winfo_children():
            w.destroy()

    # ----- Sidebar -----
    def _build_sidebar(self):
        for w in self.sidebar.winfo_children():
            w.destroy()
        self.user_area = ttk.Frame(self.sidebar, padding=10)
        self.user_area.pack(fill=tk.X)
        self.lbl_user = ttk.Label(self.user_area, text="未登录", style="Title.TLabel")
        self.lbl_user.pack()
        ttk.Separator(self.sidebar, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=6)

        nav = [
            ("主页", self._show_welcome),
            ("登录", self.show_login),
            ("注册", self.show_register),
            ("个人资料", self.show_profile),
            ("发布商品", self.show_publish),
            ("浏览商品", self.show_browse),
            ("搜索", self.show_search),
            ("我的收藏", self.show_favorites),
            ("退出登录", self.logout),
        ]
        for t, cmd in nav:
            b = ttk.Button(self.sidebar, text=t, command=cmd)
            b.pack(fill=tk.X, padx=8, pady=4)

        # Admin link (visible when admin logged in)
        if self.current_user and self.current_user.is_admin:
            ttk.Separator(self.sidebar, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=6)
            ttk.Button(self.sidebar, text="管理员后台", command=self.show_admin_panel).pack(fill=tk.X, padx=8, pady=4)

    # ----- Welcome -----
    def _show_welcome(self):
        self._clear_main()
        frame = ttk.Frame(self.main, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)
        ttk.Label(frame, text="欢迎来到二手商品平台", style="Title.TLabel").pack(pady=10)
        ttk.Label(frame, text="使用左侧菜单快速导航。").pack(pady=6)
        actions = ttk.Frame(frame)
        actions.pack(pady=20)
        ttk.Button(actions, text="浏览商品", command=self.show_browse).grid(row=0, column=0, padx=8)
        ttk.Button(actions, text="发布商品", command=self.show_publish).grid(row=0, column=1, padx=8)

    # ----- Register -----
    def show_register(self):
        self._clear_main()
        frame = ttk.Frame(self.main, padding=12)
        frame.pack(fill=tk.BOTH, expand=True)
        ttk.Label(frame, text="注册新用户", style="Title.TLabel").grid(row=0, column=0, columnspan=2, pady=6)
        labels = ["email", "phone", "password", "nickname"]
        entries = {}
        for i, lab in enumerate(labels, start=1):
            ttk.Label(frame, text=lab.capitalize()).grid(row=i, column=0, sticky=tk.E, pady=4)
            ent = ttk.Entry(frame)
            ent.grid(row=i, column=1, sticky=tk.W, pady=4)
            entries[lab] = ent

        def submit():
            data = {k: v.get().strip() for k, v in entries.items()}
            if not data["email"] or not data["password"]:
                messagebox.showwarning("提示", "Email 与 Password 为必填")
                return
            if any(u.email == data["email"] for u in self.storage.users):
                messagebox.showerror("错误", "该邮箱已被注册")
                return
            uid = ensure_int_id([u.userId for u in self.storage.users])
            user = User(uid, data["email"], data["phone"], data["password"], data["nickname"])
            self.storage.users.append(user)
            self.storage.save_users()
            messagebox.showinfo("成功", "注册成功并已登录")
            self.current_user = user
            self.lbl_user.config(text=user.nickname)
            self._build_sidebar()
            self._show_welcome()

        ttk.Button(frame, text="提交", command=submit).grid(row=6, column=0, columnspan=2, pady=10)

    # ----- Login -----
    def show_login(self):
        self._clear_main()
        frame = ttk.Frame(self.main, padding=12)
        frame.pack(fill=tk.BOTH, expand=True)
        ttk.Label(frame, text="用户登录", style="Title.TLabel").grid(row=0, column=0, columnspan=2, pady=6)
        ttk.Label(frame, text="Email").grid(row=1, column=0, sticky=tk.E, pady=4)
        e_email = ttk.Entry(frame)
        e_email.grid(row=1, column=1, sticky=tk.W, pady=4)
        ttk.Label(frame, text="Password").grid(row=2, column=0, sticky=tk.E, pady=4)
        e_pw = ttk.Entry(frame, show="*")
        e_pw.grid(row=2, column=1, sticky=tk.W, pady=4)

        def do_login():
            em = e_email.get().strip()
            pw = e_pw.get().strip()
            for u in self.storage.users:
                if u.email == em and u.password == pw:
                    self.current_user = u
                    messagebox.showinfo("成功", f"欢迎, {u.nickname}")
                    self._update_sidebar()
                    self._show_welcome()
                    return
            messagebox.showerror("失败", "账号或密码错误")

        ttk.Button(frame, text="登录", command=do_login).grid(row=3, column=0, columnspan=2, pady=8)

    def _update_sidebar(self):
        for w in self.sidebar.winfo_children():
            w.destroy()

        self.user_area = ttk.Frame(self.sidebar, padding=10)
        self.user_area.pack(fill=tk.X)

        if self.current_user:
            self.lbl_user = ttk.Label(self.user_area, text=self.current_user.nickname, style="Title.TLabel")
        else:
            self.lbl_user = ttk.Label(self.user_area, text="未登录", style="Title.TLabel")
        self.lbl_user.pack()

        ttk.Separator(self.sidebar, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=6)

        nav = [
            ("主页", self._show_welcome),
            ("登录", self.show_login),
            ("注册", self.show_register),
            ("个人资料", self.show_profile),
            ("发布商品", self.show_publish),
            ("浏览商品", self.show_browse),
            ("搜索", self.show_search),
            ("我的收藏", self.show_favorites),
            ("退出登录", self.logout),
        ]
        for t, cmd in nav:
            b = ttk.Button(self.sidebar, text=t, command=cmd)
            b.pack(fill=tk.X, padx=8, pady=4)

        # Admin
        if self.current_user and self.current_user.is_admin:
            ttk.Separator(self.sidebar, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=6)
            ttk.Button(self.sidebar, text="管理员后台", command=self.show_admin_panel).pack(fill=tk.X, padx=8, pady=4)

    # ----- Profile -----
    def show_profile(self):
        if not self._ensure_login():
            return
        self._clear_main()
        frame = ttk.Frame(self.main, padding=12)
        frame.pack(fill=tk.BOTH, expand=True)
        ttk.Label(frame, text="个人资料", style="Title.TLabel").grid(row=0, column=0, columnspan=2)
        u = self.current_user
        labels = ["email", "phone", "nickname"]
        entries = {}
        for i, lab in enumerate(labels, start=1):
            ttk.Label(frame, text=lab.capitalize()).grid(row=i, column=0, sticky=tk.E, pady=4)
            ent = ttk.Entry(frame)
            ent.insert(0, getattr(u, lab))
            ent.grid(row=i, column=1, sticky=tk.W, pady=4)
            entries[lab] = ent
        avatar_label = ttk.Label(frame, text=f"Avatar: {os.path.basename(u.avatar) if u.avatar else '(未设置)'}")
        avatar_label.grid(row=4, column=0, columnspan=2, pady=6)

        def pick_avatar():
            p = filedialog.askopenfilename(filetypes=[("Images", "*.png;*.jpg;*.jpeg;*.gif")])
            if p:
                saved = copy_image_to_storage(p)
                if saved:
                    u.avatar = saved
                    avatar_label.config(text=os.path.basename(saved))

        ttk.Button(frame, text="选择头像", command=pick_avatar).grid(row=5, column=0, pady=6)

        def save():
            u.updateProfile(entries["email"].get(), entries["phone"].get(), entries["nickname"].get(), u.avatar)
            self.storage.save_users()
            messagebox.showinfo("提示", "保存成功")
            self._update_sidebar()

        ttk.Button(frame, text="保存", command=save).grid(row=5, column=1)

    # ----- Publish -----
    def show_publish(self):
        if not self._ensure_login():
            return
        self._clear_main()
        frame = ttk.Frame(self.main, padding=12)
        frame.pack(fill=tk.BOTH, expand=True)
        ttk.Label(frame, text="发布新商品", style="Title.TLabel").grid(row=0, column=0, columnspan=2)
        labels = ["名称", "分类", "描述", "价格"]
        entries = {}
        for i, lab in enumerate(labels, start=1):
            ttk.Label(frame, text=lab).grid(row=i, column=0, sticky=tk.E, pady=4)
            ent = ttk.Entry(frame, width=60)
            ent.grid(row=i, column=1, sticky=tk.W, pady=4)
            entries[lab] = ent
        images: List[str] = []
        img_listbox = tk.Listbox(frame, height=4)
        img_listbox.grid(row=5, column=1, sticky=tk.W)

        def add_img():
            p = filedialog.askopenfilename(filetypes=[("Images", "*.png;*.jpg;*.jpeg;*.gif")])
            if p:
                saved = copy_image_to_storage(p)
                if saved:
                    images.append(saved)
                    img_listbox.insert(tk.END, os.path.basename(saved))
                else:
                    messagebox.showwarning("警告", "图片保存失败")

        ttk.Button(frame, text="添加图片", command=add_img).grid(row=5, column=0)

        def submit():
            name = entries["名称"].get().strip()
            if not name:
                messagebox.showwarning("提示", "名称不能为空")
                return
            pid = ensure_int_id([p.productId for p in self.storage.products])
            price = safe_float(entries["价格"].get(), 0.0)
            p = Product(pid, name, entries["分类"].get(), entries["描述"].get(), price, images.copy(),
                        self.current_user.userId, [])
            self.storage.products.append(p)
            self.storage.save_products()
            messagebox.showinfo("成功", "商品发布成功")
            self.show_browse()

        ttk.Button(frame, text="发布", command=submit).grid(row=6, column=0, columnspan=2, pady=10)

    # ----- Browse (card list) -----
    def show_browse(self):
        self._clear_main()
        container = ttk.Frame(self.main, padding=12)
        container.pack(fill=tk.BOTH, expand=True)
        header = ttk.Frame(container)
        header.pack(fill=tk.X)
        ttk.Label(header, text="商品列表", style="Title.TLabel").pack(side=tk.LEFT)
        ttk.Button(header, text="刷新", command=self.show_browse).pack(side=tk.RIGHT)

        canvas = tk.Canvas(container, background="#f6f7fb")
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        scrollable = ttk.Frame(canvas)

        scrollable.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # reversed newest first
        for p in sorted(self.storage.products, key=lambda x: x.productId, reverse=True):
            card = ttk.Frame(scrollable, style="Card.TFrame", padding=8)
            card.pack(fill=tk.X, padx=8, pady=6)
            left = ttk.Frame(card)
            left.pack(side=tk.LEFT, anchor="n")
            # image
            imgwidget = None
            if p.images:
                imgpath = p.images[0]
                img = load_image_for_ui(imgpath, size=(120, 120))
                if img:
                    # cache the image to avoid GC
                    key = f"p{p.productId}_thumb"
                    self.image_cache[key] = img
                    imgwidget = tk.Label(left, image=img)
                    imgwidget.image = img
                    imgwidget.pack()
                else:
                    ttk.Label(left, text="[图片]").pack()
            else:
                ttk.Label(left, text="[无图\n商品]").pack()
            right = ttk.Frame(card)
            right.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)
            ttk.Label(right, text=p.name, style="Title.TLabel").pack(anchor="w")
            ttk.Label(right, text=f"分类: {p.category}").pack(anchor="w")
            ttk.Label(right, text=f"价格: ¥{p.price:.2f}").pack(anchor="w")
            ttk.Label(right, text=(p.description[:120] + "...") if len(p.description) > 120 else p.description).pack(
                anchor="w", pady=6)
            btns = ttk.Frame(right)
            btns.pack(anchor="e")
            ttk.Button(btns, text="详情", command=lambda prod=p: self.show_detail(prod)).pack(side=tk.LEFT, padx=4)
            # 收藏按钮
            if self.current_user:
                fav_text = "取消收藏" if p.productId in self.current_user.favorites else "收藏"
                ttk.Button(btns, text=fav_text, command=lambda prod=p: self.toggle_favorite(prod)).pack(side=tk.LEFT,
                                                                                                        padx=4)
            if self.current_user and p.sellerId == self.current_user.userId:
                ttk.Button(btns, text="编辑", command=lambda prod=p: self.show_edit(prod)).pack(side=tk.LEFT, padx=4)
                ttk.Button(btns, text="删除", command=lambda prod=p: self._confirm_delete(prod)).pack(side=tk.LEFT,
                                                                                                      padx=4)

    # ----- Favorites -----
    def show_favorites(self):
        if not self._ensure_login():
            return
        self._clear_main()
        frame = ttk.Frame(self.main, padding=12)
        frame.pack(fill=tk.BOTH, expand=True)
        ttk.Label(frame, text="我的收藏", style="Title.TLabel").pack(anchor="w")
        favs = [p for p in self.storage.products if p.productId in self.current_user.favorites]
        if not favs:
            ttk.Label(frame, text="暂无收藏").pack(pady=20)
            return
        for p in favs:
            row = ttk.Frame(frame, padding=6)
            row.pack(fill=tk.X, pady=4)
            ttk.Label(row, text=f"{p.name} | ¥{p.price:.2f}").pack(side=tk.LEFT)
            ttk.Button(row, text="详情", command=lambda prod=p: self.show_detail(prod)).pack(side=tk.RIGHT)
            ttk.Button(row, text="取消收藏", command=lambda prod=p: self.toggle_favorite(prod)).pack(side=tk.RIGHT)

    def toggle_favorite(self, product: Product):
        if not self._ensure_login():
            return
        if product.productId in self.current_user.favorites:
            self.current_user.favorites.remove(product.productId)
            messagebox.showinfo("提示", "已取消收藏")
        else:
            self.current_user.favorites.append(product.productId)
            messagebox.showinfo("提示", "已加入收藏")
        self.storage.save_users()
        self._build_sidebar()
        self.show_browse()

    # ----- Search -----
    def show_search(self):
        self._clear_main()
        frame = ttk.Frame(self.main, padding=12)
        frame.pack(fill=tk.BOTH, expand=True)
        ttk.Label(frame, text="搜索商品", style="Title.TLabel").pack(anchor="w")
        searchbar = ttk.Frame(frame)
        searchbar.pack(fill=tk.X, pady=8)
        kw = ttk.Entry(searchbar)
        kw.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)
        ttk.Button(searchbar, text="搜索", command=lambda: self._do_search(kw.get())).pack(side=tk.LEFT)
        self._search_results = ttk.Frame(frame)
        self._search_results.pack(fill=tk.BOTH, expand=True)

    def _do_search(self, keyword):
        kw = keyword.strip().lower()
        for w in self._search_results.winfo_children():
            w.destroy()
        if not kw:
            ttk.Label(self._search_results, text="请输入关键词").pack()
            return
        found = [p for p in self.storage.products if kw in p.name.lower() or kw in p.description.lower()]
        if not found:
            ttk.Label(self._search_results, text="没有找到匹配项").pack()
            return
        for p in found:
            card = ttk.Frame(self._search_results, style="Card.TFrame", padding=8)
            card.pack(fill=tk.X, pady=6)
            ttk.Label(card, text=p.name, style="Title.TLabel").pack(anchor="w")
            ttk.Label(card, text=f"价格: ¥{p.price:.2f}").pack(anchor="w")
            ttk.Button(card, text="详情", command=lambda prod=p: self.show_detail(prod)).pack(anchor="e")

    # ----- Detail & Comments -----
    def show_detail(self, product: Product):
        self._clear_main()
        frame = ttk.Frame(self.main, padding=12)
        frame.pack(fill=tk.BOTH, expand=True)
        ttk.Label(frame, text=product.name, style="Title.TLabel").pack(anchor="w")
        top = ttk.Frame(frame)
        top.pack(fill=tk.X, pady=8)
        left = ttk.Frame(top)
        left.pack(side=tk.LEFT)
        if product.images:
            pth = product.images[0]
            img = load_image_for_ui(pth, size=(220, 220))
            if img:
                key = f"detail_p{product.productId}_img"
                self.image_cache[key] = img
                lbl = tk.Label(left, image=img)
                lbl.image = img
                lbl.pack()
            else:
                ttk.Label(left, text="[图片不可用]").pack()
        else:
            ttk.Label(left, text="[无图片]").pack()
        right = ttk.Frame(top)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=12)
        ttk.Label(right, text=f"分类: {product.category}").pack(anchor="w")
        ttk.Label(right, text=f"价格: ¥{product.price:.2f}").pack(anchor="w")
        seller = next((u for u in self.storage.users if u.userId == product.sellerId), None)
        seller_text = seller.nickname if seller else f"ID:{product.sellerId}"
        ttk.Label(right, text=f"卖家: {seller_text}").pack(anchor="w")
        # favorites toggle
        if self.current_user:
            fav_text = "取消收藏" if product.productId in self.current_user.favorites else "收藏"
            ttk.Button(right, text=fav_text, command=lambda prod=product: self.toggle_favorite(prod)).pack(anchor="e",
                                                                                                           pady=6)
        ttk.Label(frame, text="描述:", style="Title.TLabel").pack(anchor="w", pady=(10, 0))
        txt = tk.Text(frame, height=6, wrap="word")
        txt.insert("1.0", product.description)
        txt.config(state="disabled")
        txt.pack(fill=tk.BOTH, expand=True)

        # comments area
        ttk.Label(frame, text="留言板（按时间顺序）", style="Title.TLabel").pack(anchor="w", pady=(8, 0))
        comments_frame = ttk.Frame(frame)
        comments_frame.pack(fill=tk.BOTH, expand=True)
        # show comments
        if not product.comments:
            ttk.Label(comments_frame, text="暂无留言").pack()
        else:
            for c in product.comments:
                comm_box = ttk.Frame(comments_frame, padding=6, relief="groove")
                comm_box.pack(fill=tk.X, pady=4)
                ttk.Label(comm_box, text=f"{c.get('nickname', '匿名')}：").pack(anchor="w")
                ttk.Label(comm_box, text=c.get("text", "")).pack(anchor="w")
        # posting comment
        if self.current_user:
            post_frame = ttk.Frame(frame)
            post_frame.pack(fill=tk.X, pady=8)
            ttk.Label(post_frame, text="写留言：").pack(anchor="w")
            comment_ent = ttk.Entry(post_frame, width=80)
            comment_ent.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)

            def post_comment():
                txtc = comment_ent.get().strip()
                if not txtc:
                    messagebox.showwarning("提示", "留言不能为空")
                    return
                product.comments.append(
                    {"userId": self.current_user.userId, "nickname": self.current_user.nickname, "text": txtc})
                self.storage.save_products()
                messagebox.showinfo("提示", "留言已发布")
                self.show_detail(product)  # refresh

            ttk.Button(post_frame, text="发布", command=post_comment).pack(side=tk.LEFT, padx=4)

        # owner actions: edit/delete
        if self.current_user and product.sellerId == self.current_user.userId:
            act = ttk.Frame(frame)
            act.pack(anchor="e", pady=8)
            ttk.Button(act, text="编辑", command=lambda p=product: self.show_edit(p)).pack(side=tk.LEFT, padx=6)
            ttk.Button(act, text="删除", command=lambda p=product: self._confirm_delete(p)).pack(side=tk.LEFT, padx=6)

    # ----- Edit -----
    def show_edit(self, product: Product):
        if not self._ensure_login():
            return
        if not (self.current_user and product.sellerId == self.current_user.userId):
            messagebox.showerror("错误", "没有权限编辑该商品")
            return
        self._clear_main()
        frame = ttk.Frame(self.main, padding=12)
        frame.pack(fill=tk.BOTH, expand=True)
        ttk.Label(frame, text="编辑商品", style="Title.TLabel").grid(row=0, column=0, columnspan=2)
        labels = ["名称", "分类", "描述", "价格"]
        entries = {}
        for i, lab in enumerate(labels, start=1):
            ttk.Label(frame, text=lab).grid(row=i, column=0, sticky=tk.E, pady=4)
            ent = ttk.Entry(frame, width=60)
            # map fields
            if lab == "名称":
                ent.insert(0, product.name)
            elif lab == "分类":
                ent.insert(0, product.category)
            elif lab == "描述":
                ent.insert(0, product.description)
            elif lab == "价格":
                ent.insert(0, str(product.price))
            ent.grid(row=i, column=1, sticky=tk.W, pady=4)
            entries[lab] = ent
        images = product.images.copy()
        listbox = tk.Listbox(frame, height=4)
        for im in images:
            listbox.insert(tk.END, os.path.basename(im))
        listbox.grid(row=5, column=1, sticky=tk.W)

        def add_img():
            pth = filedialog.askopenfilename(filetypes=[("Images", "*.png;*.jpg;*.jpeg;*.gif")])
            if pth:
                saved = copy_image_to_storage(pth)
                if saved:
                    images.append(saved)
                    listbox.insert(tk.END, os.path.basename(saved))
                else:
                    messagebox.showwarning("警告", "图片保存失败")

        ttk.Button(frame, text="添加图片", command=add_img).grid(row=5, column=0)

        def save():
            name = entries["名称"].get().strip()
            price = safe_float(entries["价格"].get(), product.price)
            category = entries["分类"].get().strip()
            description = entries["描述"].get().strip()
            product.edit(name, category, description, price, images.copy())
            self.storage.save_products()
            messagebox.showinfo("提示", "保存成功")
            self.show_detail(product)

        ttk.Button(frame, text="保存", command=save).grid(row=6, column=0, columnspan=2, pady=8)

    # ----- Delete -----
    def _confirm_delete(self, product: Product):
        if not self._ensure_login():
            return
        if messagebox.askyesno("确认", "确定删除该商品？"):
            # remove product
            self.storage.products = [p for p in self.storage.products if p.productId != product.productId]
            # also remove productId from any user's favorites
            for u in self.storage.users:
                if product.productId in u.favorites:
                    u.favorites.remove(product.productId)
            self.storage.save_products()
            self.storage.save_users()
            messagebox.showinfo("提示", "已删除")
            self.show_browse()

    # ----- Helpers -----
    def _ensure_login(self):
        if not self.current_user:
            if messagebox.askyesno("未登录", "需要登录才能进行此操作，是否现在登录？"):
                self.show_login()
                return False
            return False
        return True

    def logout(self):
        if self.current_user and messagebox.askyesno("退出", "确认退出登录？"):
            self.current_user = None
            self.lbl_user.config(text="未登录")
            self._build_sidebar()
            self._show_welcome()

    # ----- Admin Panel -----
    def show_admin_panel(self):
        if not (self.current_user and self.current_user.is_admin):
            messagebox.showerror("错误", "需要管理员权限")
            return
        self._clear_main()
        frame = ttk.Frame(self.main, padding=12)
        frame.pack(fill=tk.BOTH, expand=True)
        ttk.Label(frame, text="管理员后台", style="Title.TLabel").pack(anchor="w", pady=4)

        tab_control = ttk.Notebook(frame)
        tab_users = ttk.Frame(tab_control)
        tab_products = ttk.Frame(tab_control)
        tab_control.add(tab_users, text="用户管理")
        tab_control.add(tab_products, text="商品管理")
        tab_control.pack(fill=tk.BOTH, expand=True, pady=8)

        # Users tab
        users_frame = ttk.Frame(tab_users, padding=8)
        users_frame.pack(fill=tk.BOTH, expand=True)
        users_list = tk.Listbox(users_frame)
        users_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        for u in self.storage.users:
            users_list.insert(tk.END, f"ID:{u.userId} {u.nickname} <{u.email}> {'(admin)' if u.is_admin else ''}")
        users_ops = ttk.Frame(users_frame)
        users_ops.pack(side=tk.RIGHT, fill=tk.Y)

        def del_user():
            sel = users_list.curselection()
            if not sel:
                messagebox.showwarning("提示", "请选择要删除的用户")
                return
            idx = sel[0]
            target = self.storage.users[idx]
            if target.is_admin:
                messagebox.showerror("错误", "不能删除管理员账户")
                return
            if messagebox.askyesno("确认", f"确定删除用户 {target.nickname} ? 其商品也将被删除"):
                # delete user's products
                self.storage.products = [p for p in self.storage.products if p.sellerId != target.userId]
                # delete user
                del self.storage.users[idx]
                self.storage.save_products()
                self.storage.save_users()
                messagebox.showinfo("提示", "用户与其商品已删除")
                self.show_admin_panel()

        ttk.Button(users_ops, text="删除用户", command=del_user).pack(pady=6)

        # Products tab
        products_frame = ttk.Frame(tab_products, padding=8)
        products_frame.pack(fill=tk.BOTH, expand=True)
        prod_list = tk.Listbox(products_frame)
        prod_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        for p in self.storage.products:
            prod_list.insert(tk.END, f"ID:{p.productId} {p.name} | ¥{p.price:.2f} | 卖家ID:{p.sellerId}")
        prod_ops = ttk.Frame(products_frame)
        prod_ops.pack(side=tk.RIGHT, fill=tk.Y)

        def del_product_admin():
            sel = prod_list.curselection()
            if not sel:
                messagebox.showwarning("提示", "请选择要删除的商品")
                return
            idx = sel[0]
            target = self.storage.products[idx]
            if messagebox.askyesno("确认", f"确定删除商品 {target.name} ?"):
                pid = target.productId
                self.storage.products = [p for p in self.storage.products if p.productId != pid]
                for u in self.storage.users:
                    if pid in u.favorites:
                        u.favorites.remove(pid)
                self.storage.save_products()
                self.storage.save_users()
                messagebox.showinfo("提示", "商品已删除")
                self.show_admin_panel()

        ttk.Button(prod_ops, text="删除商品", command=del_product_admin).pack(pady=6)

    # ----- Run -----
    def run(self):
        self.root.mainloop()


# ---------------------------
# Entry point
# ---------------------------
if __name__ == "__main__":
    app = SecondHandApp()
    app.run()
