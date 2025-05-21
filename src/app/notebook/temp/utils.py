import pandas as pd


def normalize_list_column(df):
    result = []
    for idx, row in df.iterrows():
        row_dict = {}
        for col_nm in df.columns:
            if "list" in col_nm:
                try:
                    row_value = eval(row[col_nm])
                except:
                    row_value = [row[col_nm]]
                    pass
                if isinstance(row_value, list):
                    row_dict[col_nm] = row_value
                else:
                    row_value = row_value.split(",")
                    row_dict[col_nm] = [row_value]

            else:
                row_dict[col_nm] = row[col_nm]
            result.append(row_dict)
    return pd.DataFrame(result)


def split_operation_period(df, period_field):
    """
    '시작일~종료일' 형식의 기간 문자열을 두 개의 날짜 타입 필드로 분리합니다.

    Parameters:
    -----------
    df : pandas.DataFrame
        처리할 DataFrame
    period_field : str
        '시작일~종료일' 형식의 값을 가진 필드명

    Returns:
    --------
    pandas.DataFrame
        'productoperationperiodFrom'과 'productoperationperiodTo' 컬럼이 추가된 DataFrame
    """
    # 복사본 생성 (원본 보존)
    result_df = df.copy()

    # 새 컬럼 생성
    result_df["productoperationperiodFrom"] = pd.NaT  # 날짜 타입의 NaT(Not a Time)로 초기화
    result_df["productoperationperiodTo"] = pd.NaT

    # 각 행 처리
    for idx, row in result_df.iterrows():
        period_value = row[period_field]

        # NaN 또는 빈 문자열 처리
        if pd.isna(period_value) or period_value == "":
            continue  # 이미 NaT로 초기화되어 있으므로 그대로 둠

        try:
            # '~'로 분리
            parts = period_value.split("~")
            if len(parts) == 2:
                from_date_str, to_date_str = parts

                # 날짜 형식 변환
                from_date = pd.to_datetime(from_date_str, format="%Y.%m.%d")
                try:
                    to_date = pd.to_datetime(to_date_str, format="%Y.%m.%d")
                except pd.errors.OutOfBoundsDatetime:
                    to_date = pd.to_datetime("2262.04.11", format="%Y.%m.%d")

                # 결과 DataFrame에 저장
                result_df.at[idx, "productoperationperiodFrom"] = from_date
                result_df.at[idx, "productoperationperiodTo"] = to_date
            else:
                print(f"경고: 인덱스 {idx}의 기간 형식이 예상과 다릅니다: {period_value}")
        except Exception as e:
            print(f"오류: 인덱스 {idx}의 기간 '{period_value}' 처리 중 오류 발생: {e}")

    return result_df
