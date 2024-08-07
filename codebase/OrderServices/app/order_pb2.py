# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: order.proto
"""Generated protocol buffer code."""
from google.protobuf.internal import builder as _builder
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import symbol_database as _symbol_database
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()




DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\x0border.proto\x12\x05order\"\xda\x02\n\x07Payment\x12\n\n\x02id\x18\x01 \x01(\x05\x12\x12\n\npayment_id\x18\x02 \x01(\t\x12\x10\n\x08order_id\x18\x03 \x01(\t\x12\x0f\n\x07user_id\x18\x04 \x01(\t\x12\x10\n\x08username\x18\x05 \x01(\t\x12\r\n\x05\x65mail\x18\x06 \x01(\t\x12\x10\n\x08password\x18\x07 \x01(\t\x12\x0e\n\x06\x61mount\x18\x08 \x01(\x02\x12\x13\n\x0b\x63\x61rd_number\x18\t \x01(\x03\x12\x11\n\texp_month\x18\n \x01(\x05\x12\x10\n\x08\x65xp_year\x18\x0b \x01(\x05\x12\x0b\n\x03\x63vc\x18\x0c \x01(\x05\x12,\n\x0epayment_status\x18\r \x01(\x0e\x32\x14.order.PaymentStatus\x12#\n\x06option\x18\x0e \x01(\x0e\x32\x13.order.SelectOption\x12\x18\n\x10http_status_code\x18\x0f \x01(\x03\x12\x15\n\rerror_message\x18\x10 \x01(\t\"\x80\x02\n\x04User\x12\n\n\x02id\x18\x01 \x01(\x05\x12\x0f\n\x07user_id\x18\x02 \x01(\t\x12\x10\n\x08username\x18\x03 \x01(\t\x12\r\n\x05\x65mail\x18\x04 \x01(\t\x12\x10\n\x08password\x18\x05 \x01(\t\x12\x14\n\x0c\x61\x63\x63\x65ss_token\x18\x06 \x01(\t\x12\x15\n\rrefresh_token\x18\x07 \x01(\t\x12%\n\x07service\x18\x08 \x01(\x0e\x32\x14.order.SelectService\x12\x15\n\rerror_message\x18\t \x01(\t\x12#\n\x06option\x18\n \x01(\x0e\x32\x13.order.SelectOption\x12\x18\n\x10http_status_code\x18\x0b \x01(\x03\"\xbd\x03\n\x05Order\x12\n\n\x02id\x18\x01 \x01(\x05\x12\x10\n\x08order_id\x18\x02 \x01(\t\x12\x12\n\nproduct_id\x18\x03 \x01(\t\x12\x0f\n\x07user_id\x18\x04 \x01(\t\x12\x10\n\x08username\x18\x05 \x01(\t\x12\r\n\x05\x65mail\x18\x06 \x01(\t\x12\x10\n\x08quantity\x18\x07 \x01(\x03\x12\x18\n\x10shipping_address\x18\x08 \x01(\t\x12\x16\n\x0e\x63ustomer_notes\x18\t \x01(\t\x12\x13\n\x0bstock_level\x18\n \x01(\x03\x12\x1c\n\x14is_product_available\x18\x0b \x01(\x08\x12\x1a\n\x12is_stock_available\x18\x0c \x01(\x08\x12\x0f\n\x07message\x18\r \x01(\t\x12\x15\n\rerror_message\x18\x0e \x01(\t\x12(\n\x0corder_status\x18\x0f \x01(\x0e\x32\x12.order.OrderStatus\x12,\n\x0epayment_status\x18\x10 \x01(\x0e\x32\x14.order.PaymentStatus\x12#\n\x06option\x18\x11 \x01(\x0e\x32\x13.order.SelectOption\x12\x18\n\x10http_status_code\x18\x12 \x01(\x03\")\n\tOrderList\x12\x1c\n\x06orders\x18\x01 \x03(\x0b\x32\x0c.order.Order*H\n\x0cSelectOption\x12\n\n\x06\x43REATE\x10\x00\x12\n\n\x06UPDATE\x10\x01\x12\n\n\x06\x44\x45LETE\x10\x02\x12\x07\n\x03GET\x10\x03\x12\x0b\n\x07GET_ALL\x10\x04*\'\n\rSelectService\x12\x0b\n\x07PAYMENT\x10\x00\x12\t\n\x05ORDER\x10\x01*-\n\x0bOrderStatus\x12\x0f\n\x0bIN_PROGRESS\x10\x00\x12\r\n\tCOMPLETED\x10\x01*2\n\rPaymentStatus\x12\x0b\n\x07PENDING\x10\x00\x12\x08\n\x04PAID\x10\x01\x12\n\n\x06\x46\x41ILED\x10\x02\x62\x06proto3')

_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, globals())
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'order_pb2', globals())
if _descriptor._USE_C_DESCRIPTORS == False:

  DESCRIPTOR._options = None
  _SELECTOPTION._serialized_start=1121
  _SELECTOPTION._serialized_end=1193
  _SELECTSERVICE._serialized_start=1195
  _SELECTSERVICE._serialized_end=1234
  _ORDERSTATUS._serialized_start=1236
  _ORDERSTATUS._serialized_end=1281
  _PAYMENTSTATUS._serialized_start=1283
  _PAYMENTSTATUS._serialized_end=1333
  _PAYMENT._serialized_start=23
  _PAYMENT._serialized_end=369
  _USER._serialized_start=372
  _USER._serialized_end=628
  _ORDER._serialized_start=631
  _ORDER._serialized_end=1076
  _ORDERLIST._serialized_start=1078
  _ORDERLIST._serialized_end=1119
# @@protoc_insertion_point(module_scope)
