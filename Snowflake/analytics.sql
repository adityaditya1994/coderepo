Find top performing products from each store type and tier

select * from ahs_store_lt_tier_item_type
qualify rank() over(partition by outlet_location_type , tier order by tier asc, total_sales desc ) =1 
order by outlet_location_type, tier
;
