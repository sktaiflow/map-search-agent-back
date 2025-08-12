"""
Utility functions for data preprocessing
"""
import ast
import pandas as pd
from typing import List, Union, Dict, Any


def extract_sub_field(data: Any, sub_field_name: str) -> Any:
    """Extract sub-field from nested data structure."""
    if isinstance(data, str):
        try:
            data = ast.literal_eval(data)
        except:
            return None
        
    if isinstance(data, list) and len(data) == 1:
        first_item = data[0]
        if isinstance(first_item, dict) and sub_field_name in first_item:
            sub_field_obj = first_item[sub_field_name]
            if isinstance(sub_field_obj, dict) and 'value' in sub_field_obj:
                return sub_field_obj['value']
            elif isinstance(sub_field_obj, dict) and 'valueList' in sub_field_obj:
                return sub_field_obj['valueList']
    elif isinstance(data, list) and len(data) > 1:
        raise ValueError(f"Expected a single item in the list, but found multiple items.")
    
    return None


def extract_val(data: Any, keys: Union[str, List[str]]) -> Any:
    """Recursively extract value from nested dictionary."""
    if data is None:
        return None
        
    if isinstance(keys, str):
        try:
            return data.get(keys) if isinstance(data, dict) else None
        except:
            return None
        
    elif isinstance(keys, list) and len(keys) > 0:
        if len(keys) == 1:
            return data.get(keys[0]) if isinstance(data, dict) else None
        else:
            first_key = keys[0]
            remaining_keys = keys[1:]
            next_data = data.get(first_key) if isinstance(data, dict) else None
            return extract_val(next_data, remaining_keys)
    else:
        return None


def str_to_num(x: Any) -> int:
    """Convert string with units (분, 건) to number."""
    if pd.isna(x):
        return 0
    if x == '무제한':
        return 99999
    elif isinstance(x, str) and x.endswith(('분', '건')):
        try:
            return int(x[:-1])
        except ValueError:
            return 0
    else:
        return 0


def to_gb(x: Any) -> float:
    """Convert data size string to GB."""
    if pd.isna(x):
        return 0.0
    if x == '무제한':
        return 99999.0
    elif isinstance(x, str):
        if x.endswith('GB'):
            try:
                return float(x.replace('GB', ''))
            except ValueError:
                return 0.0
        elif x.endswith('MB'):
            try:
                return float(x.replace('MB', '')) / 1024
            except ValueError:
                return 0.0
    return 0.0


def to_mbps(x: Any) -> float:
    """Convert speed string to Mbps."""
    if pd.isna(x) or not isinstance(x, str):
        return 0.0
    
    x = x.strip()
    if x.lower().endswith('mbps'):
        return float(x.lower().replace('mbps', ''))
    elif x.lower().endswith('kbps'):
        return float(x.lower().replace('kbps', '')) / 1000
    else:
        return 0.0


def remove_won(x: Any) -> int:
    """Remove '원' and convert to integer."""
    if pd.isna(x):
        return 0
    if isinstance(x, str):
        return int(x.replace('원', '').replace(',', '').strip())
    return int(x)


def safe_literal_eval(data: Any) -> Any:
    """Safely evaluate string as literal."""
    if isinstance(data, str):
        try:
            return ast.literal_eval(data)
        except:
            return None
    return data


def parse_offer_benefits(data: Any) -> List[Dict[str, str]]:
    """Parse allOfferBenefits data to extract product information."""
    def parse_list(list_data: List[Dict]) -> List[Dict[str, str]]:
        result_data = []
        for item in list_data:
            product_list = extract_val(item, ['benefitInfo', 'productInformation', 'productList'])
            if product_list:
                for product in product_list:
                    result_data.append({
                        'productId': product.get('pmProductId', ''),
                        'productName': product.get('productName', '')
                    })
        return result_data if result_data else None

    if isinstance(data, dict):
        return parse_list([data])
    elif isinstance(data, list):
        return parse_list(data)
    else:
        try:
            data = ast.literal_eval(str(data))
            return parse_list(data if isinstance(data, list) else [data])
        except:
            return None


def parse_data_option_providing_method(data: Any) -> List[Dict[str, str]]:
    """Parse dataOptionProvidingMethod data to extract option information."""
    def parse_list(list_data: List[Dict]) -> List[Dict[str, str]]:
        result_data = []
        for item in list_data:
            name = extract_val(item, ['detailedDataOptionName', 'value'])
            id_val = extract_val(item, ['legacyDataOptionCode', 'value'])
            code = extract_val(item, ['pmDataOptionCode', 'value'])
            data_amount = extract_val(item, ['dataOptionProvidingRecord', 'dataOptionExtraData', 'dataAmount', 'value'])
            discount_rate = extract_val(item, ['dataOptionProvidingRecord', 'dataSubtractionDiscountRate', 'rateDiscount', 'value'])
            monthly_price = extract_val(item, ['dataOptionProvidingRecord', 'dataOptionMonthlyPrice', 'value'])
            
            result_data.append({
                "productId": id_val,
                "productName": name,
                "pmDataOptionCode": code,
                "extradataAmount": data_amount,
                "monthlyPrice": monthly_price,
                "DiscountRate": discount_rate
            })
        return result_data if result_data else None

    if isinstance(data, dict):
        return parse_list([data])
    elif isinstance(data, list):
        return parse_list(data)
    else:
        try:
            data = ast.literal_eval(str(data))
            return parse_list(data if isinstance(data, list) else [data])
        except:
            return None


def create_table_from_config(df: pd.DataFrame, table_name: str, table_config: Dict) -> pd.DataFrame:
    """Create a table based on configuration."""
    source_cols = table_config['source_cols']
    target_cols = table_config['target_cols']
    
    # Check which columns exist in the dataframe
    existing_cols = [col for col in source_cols if col in df.columns]
    
    if not existing_cols:
        print(f"Warning: No columns found for {table_name}")
        return pd.DataFrame()
    
    # Create the table
    table_df = df[existing_cols].copy()
    
    # Rename columns if target_cols is provided
    if len(existing_cols) == len(target_cols):
        table_df.columns = target_cols[:len(existing_cols)]
    
    return table_df


def merge_product_lists(df: pd.DataFrame, group_col: str, product_col: str) -> List[List[Dict]]:
    """Merge group and product lists for relation tables."""
    result_list = []
    
    for i in range(len(df)):
        group_value = df[group_col].iloc[i] if group_col in df.columns else []
        product_value = df[product_col].iloc[i] if product_col in df.columns else []
        
        # Extract group list if exists
        group_list = []
        if group_value and len(group_value) > 0:
            try:
                if isinstance(group_value[0], dict) and 'groupList' in group_value[0]:
                    group_list = group_value[0]['groupList']
            except (IndexError, TypeError):
                pass
        
        # Combine with product list
        combined_list = group_list + (product_value if product_value else [])
        result_list.append(combined_list)
    
    return result_list


def process_relation_data(df: pd.DataFrame, source_col: str, relation_type: str) -> pd.DataFrame:
    """Process relation data into standardized format."""
    if source_col not in df.columns:
        return pd.DataFrame()
    
    tmp_df = df[['pmProductID', source_col]].copy()
    tmp_df = tmp_df.explode(column=source_col)
    tmp_df = tmp_df.reset_index(drop=True)
    tmp_df = tmp_df[~tmp_df[source_col].isnull()]
    tmp_df = tmp_df.reset_index(drop=True)
    
    if len(tmp_df) == 0:
        return pd.DataFrame()
    
    # Extract product information based on data structure
    if 'pmProductId' in str(tmp_df[source_col].iloc[0]):
        tmp_df['productId'] = tmp_df[source_col].apply(lambda x: x.get('pmProductId', '') if isinstance(x, dict) else '')
        tmp_df['productName'] = tmp_df[source_col].apply(lambda x: x.get('productName', '') if isinstance(x, dict) else '')
    else:
        tmp_df['productId'] = tmp_df[source_col].apply(lambda x: x.get('productId', '') if isinstance(x, dict) else '')
        tmp_df['productName'] = tmp_df[source_col].apply(lambda x: x.get('productName', '') if isinstance(x, dict) else '')
    
    tmp_df['type'] = relation_type
    tmp_df.drop(columns=[source_col], inplace=True)
    
    return tmp_df


def remove_duplicates_keep_concurrent(relation_df: pd.DataFrame) -> pd.DataFrame:
    """Remove duplicates, keeping concurrent termination over pre-termination."""
    relation_df['relationID'] = relation_df['pmProductID'] + '_' + relation_df['productId'].fillna('')
    
    # Count occurrences
    duplicate_counts = relation_df['relationID'].value_counts()
    duplicated_ids = duplicate_counts[duplicate_counts >= 2].index
    
    # Remove pre-termination when concurrent exists
    mask = ~((relation_df['relationID'].isin(duplicated_ids)) & 
             (relation_df['type'] == 'productRelation.signupPreTermination.productList'))
    
    return relation_df[mask].reset_index(drop=True)