Store_location_type_size:


create or replace transient table
ahs_store_lt_sz
(outlet_location_type varchar,
outlet_size varchar,
Total_Sales number,
Item_Sold number) ;


Store_location_tier_item_type:

create or replace transient table
ahs_store_lt_tier_item_type
(outlet_location_type varchar,
tier varchar,
item_type varchar,
Total_Sales number,
Item_Sold number) ;



item_type:

create or replace transient table
ahs_item_type
(
item_type varchar,
Total_Sales number,
Item_Sold number) ;

