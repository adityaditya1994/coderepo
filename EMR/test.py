



spark-submit --deploy-mode cluster



--conf “spark.yarn.appMasterEnv.SRC_DIR=s3://ahs-emr-demo-17oct/source/” --conf “spark.yarn.appMasterEnv. SRC_FILE_PATTERN=2021-01-13”
--py-files s3://ahs-emr-demo-17oct/app_code/spark_code/spark_code.zip


s3://ahs-emr-demo-17oct/app_code/app.py