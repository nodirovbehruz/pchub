import graphene
from graphene_django.debug import DjangoDebug
import apps.computers.schema
import apps.billing.schema
import apps.shops.schema
import apps.accounts.schema


class Query(
    apps.computers.schema.Query,
    apps.billing.schema.Query,
    apps.shops.schema.Query,
    apps.accounts.schema.Query,
    graphene.ObjectType
):
    debug = graphene.Field(DjangoDebug, name="_debug")

class Mutation(
    apps.computers.schema.Mutation,
    apps.billing.schema.Mutation,
    apps.shops.schema.Mutation,
    apps.accounts.schema.Mutation,
    graphene.ObjectType
):
    pass

schema = graphene.Schema(query=Query, mutation=Mutation)
