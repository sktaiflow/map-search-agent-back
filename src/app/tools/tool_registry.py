from src.app.tools.prod_meta_tools import prod_meta_search
from src.app.tools.user_tools import get_service_info, get_subscribed_products

tool_registry = {
    "prod_meta_search": {
        "func": prod_meta_search,
        "args": ["query"]
    },
    "get_service_info": {
        "func": get_service_info,
        "args": ["svc_mgmt_num"]
    },
    "get_subscribed_products": {
        "func": get_subscribed_products,
        "args": ["svc_mgmt_num"]
    }
}