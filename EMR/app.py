import os
from util import get_spark_session
from read import from_files
from write import write
from process import transform


def main():
    env = os.environ.get('ENVIRON')
    src_dir = os.environ.get('SRC_DIR')
    file_pattern = f"{os.environ.get('SRC_FILE_PATTERN')}-*"
    src_file_format = os.environ.get('SRC_FILE_FORMAT')
    tgt_dir = os.environ.get('TGT_DIR')
    tgt_file_format = os.environ.get('TGT_FILE_FORMAT')
    spark = get_spark_session(env, 'Aditya Spark Demo')
    df = from_files(spark, src_dir, file_pattern, src_file_format) ## E (Extract)
    df_transformed = transform(df) ## Transformation
    write(df_transformed, tgt_dir, tgt_file_format) ##Load


if __name__ == '__main__':
    main()