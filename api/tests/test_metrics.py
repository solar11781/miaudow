from main import monthly_aggregation,valid_value,retrieve

def test_power_missing_sentinel_is_null():
    assert valid_value(-999.0) is None
    assert valid_value(None) is None

def test_no_invented_months():
    months=monthly_aggregation({'PRECTOTCORR':{'20240101':12},'T2M_MAX':{'20240101':31}},2024)
    assert len(months)==12
    assert months[0]['precipitation_mm'] is None
    assert months[0]['temp_max_c'] is None
    assert months[1]['precipitation_mm'] is None

def test_full_month_exact_aggregation():
    r={f'202402{i:02}':2 for i in range(1,30)}
    t={f'202402{i:02}':30+i/10 for i in range(1,30)}
    row=monthly_aggregation({'PRECTOTCORR':r,'T2M_MAX':t},2024)[1]
    assert row['precipitation_mm']==58.0
    assert row['day_count']==29
    assert row['temp_max_c']==31.5

def test_retrieval_missing_evidence():
    assert retrieve('câu hỏi không liên quan xe hơi')==[]
