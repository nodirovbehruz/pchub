import graphene
from graphene_django.types import DjangoObjectType
from apps.shops.models.product import Product
from apps.shops.models.order import Order, OrderItem
from apps.shops.models.category import Category


class CategoryType(graphene.ObjectType):
    id = graphene.ID()
    name = graphene.String()
    slug = graphene.String()
    product_count = graphene.Int()


class ProductType(graphene.ObjectType):
    id = graphene.ID()
    name = graphene.String()
    description = graphene.String()
    price = graphene.Float()
    purchase_price = graphene.Float()
    original_price = graphene.Float()
    current_stock = graphene.Int()
    is_active = graphene.Boolean()
    shell_display = graphene.Boolean()
    barcode = graphene.String()
    category_name = graphene.String()
    category_id = graphene.ID()

    def resolve_price(self, info):
        return float(self.price)

    def resolve_purchase_price(self, info):
        return float(self.purchase_price) if self.purchase_price else None

    def resolve_original_price(self, info):
        return float(self.original_price) if self.original_price else None

    def resolve_category_name(self, info):
        return self.category.name if self.category_id else '—'

    def resolve_category_id(self, info):
        return str(self.category_id) if self.category_id else None


class ServiceType(graphene.ObjectType):
    id = graphene.ID()
    name = graphene.String()
    price = graphene.Float()
    original_price = graphene.Float()
    is_active = graphene.Boolean()

    def resolve_price(self, info):
        return float(self.price)


class Query(graphene.ObjectType):
    products = graphene.List(ProductType, search=graphene.String(), category_id=graphene.ID())
    services = graphene.List(ServiceType)
    categories = graphene.List(CategoryType)

    def resolve_categories(self, info, **kwargs):
        return [
            CategoryType(id=str(c.id), name=c.name, slug=c.slug, product_count=c.product_count)
            for c in Category.objects.filter(is_active=True)
        ]

    def resolve_products(self, info, search=None, category_id=None, **kwargs):
        qs = Product.objects.select_related('category')
        if category_id:
            qs = qs.filter(category_id=category_id)
        if search:
            qs = qs.filter(name__icontains=search)
        return qs

    def resolve_services(self, info, **kwargs):
        # Services are Products in a "Услуги" category 
        try:
            service_cat = Category.objects.get(slug='services')
            return Product.objects.filter(category=service_cat)
        except Category.DoesNotExist:
            return Product.objects.none()


class CreateProductMutation(graphene.Mutation):
    class Arguments:
        name = graphene.String(required=True)
        price = graphene.Float(required=True)
        purchase_price = graphene.Float()
        original_price = graphene.Float()
        category_id = graphene.ID(required=True)
        description = graphene.String()
        barcode = graphene.String()
        shell_display = graphene.Boolean()

    success = graphene.Boolean()
    product = graphene.Field(ProductType)

    @classmethod
    def mutate(cls, root, info, name, price, category_id, purchase_price=None, original_price=None, description='', barcode=None, shell_display=True):
        from django.utils.text import slugify
        try:
            cat = Category.objects.get(id=category_id)
            slug_base = slugify(name) or f'product-{name}'
            slug = slug_base
            i = 1
            while Product.objects.filter(slug=slug).exists():
                slug = f'{slug_base}-{i}'
                i += 1
            p = Product.objects.create(
                name=name, slug=slug, price=price,
                purchase_price=purchase_price,
                original_price=original_price,
                description=description or '',
                barcode=barcode,
                shell_display=shell_display,
                category=cat, is_active=True
            )
            # Initialize stock for new product
            from apps.shops.models.stock import Stock
            Stock.objects.create(product=p, quantity=0)
            
            return CreateProductMutation(success=True, product=p)
        except Exception as e:
            return CreateProductMutation(success=False, product=None)


class UpdateProductMutation(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)
        name = graphene.String()
        price = graphene.Float()
        purchase_price = graphene.Float()
        original_price = graphene.Float()
        is_active = graphene.Boolean()
        shell_display = graphene.Boolean()
        description = graphene.String()
        barcode = graphene.String()

    success = graphene.Boolean()

    @classmethod
    def mutate(cls, root, info, id, name=None, price=None, purchase_price=None, original_price=None, is_active=None, shell_display=None, description=None, barcode=None):
        try:
            p = Product.objects.get(id=id)
            if name is not None: p.name = name
            if price is not None: p.price = price
            if purchase_price is not None: p.purchase_price = purchase_price
            if original_price is not None: p.original_price = original_price
            if is_active is not None: p.is_active = is_active
            if shell_display is not None: p.shell_display = shell_display
            if description is not None: p.description = description
            if barcode is not None: p.barcode = barcode
            p.save()
            return UpdateProductMutation(success=True)
        except Product.DoesNotExist:
            return UpdateProductMutation(success=False)


class DeleteProductMutation(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    success = graphene.Boolean()

    @classmethod
    def mutate(cls, root, info, id):
        try:
            Product.objects.get(id=id).delete()
            return DeleteProductMutation(success=True)
        except:
            return DeleteProductMutation(success=False)


class CreateCategoryMutation(graphene.Mutation):
    class Arguments:
        name = graphene.String(required=True)

    success = graphene.Boolean()
    category = graphene.Field(CategoryType)

    @classmethod
    def mutate(cls, root, info, name):
        from django.utils.text import slugify
        slug_base = slugify(name) or f'cat-{name}'
        slug = slug_base
        i = 1
        while Category.objects.filter(slug=slug).exists():
            slug = f'{slug_base}-{i}'
            i += 1
        cat = Category.objects.create(name=name, slug=slug, is_active=True)
        return CreateCategoryMutation(success=True, category=CategoryType(id=str(cat.id), name=cat.name, slug=cat.slug, product_count=0))


class AdjustStockMutation(graphene.Mutation):
    class Arguments:
        product_id = graphene.ID(required=True)
        quantity = graphene.Int(required=True)
        reason = graphene.String()

    success = graphene.Boolean()
    current_stock = graphene.Int()

    @classmethod
    def mutate(cls, root, info, product_id, quantity, reason=''):
        from apps.shops.models.stock import Stock
        try:
            stock = Stock.objects.get(product_id=product_id)
            new_val = stock.adjust_stock(quantity, reason=reason)
            return AdjustStockMutation(success=True, current_stock=new_val)
        except Stock.DoesNotExist:
            p = Product.objects.get(id=product_id)
            stock = Stock.objects.create(product=p, quantity=quantity)
            return AdjustStockMutation(success=True, current_stock=quantity)
        except Exception as e:
            return AdjustStockMutation(success=False)


class Mutation(graphene.ObjectType):
    create_product = CreateProductMutation.Field()
    update_product = UpdateProductMutation.Field()
    delete_product = DeleteProductMutation.Field()
    create_category = CreateCategoryMutation.Field()
    adjust_stock = AdjustStockMutation.Field()
