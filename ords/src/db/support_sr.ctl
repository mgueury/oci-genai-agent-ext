load data
infile 'support_sr.csv'
into table support_sr
fields terminated by "," optionally enclosed by '"'
( owner_id
  id,
  customer_name,
  subject,
  question CHAR(20000),
  answer
)
