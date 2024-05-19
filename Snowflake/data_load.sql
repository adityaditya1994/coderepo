DataLoad  ahs_store_location_type_size :

copy into ahs_store_lt_sz
from (
select $1::varchar, $2, $3, $4 from @ahs_sales_s3/target_data/Location_Outlet/
(file_format => my_csv_format ));


DataLoad  ahs_store_location_type_size :
copy into ahs_store_lt_tier_item_type
from (
select $1::varchar, $2, $3, $4, $5 from @ahs_sales_s3/target_data/outlet_location_item/
(file_format => my_csv_format ));


DataLoad  item_type :

copy into ahs_item_type
from (
select $1, $2, $3 from @ahs_sales_s3/target_data/sales_item_type/
(file_format => my_csv_format )
);





