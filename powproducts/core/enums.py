"""Core enums for PowProducts."""

from enum import Enum


class ProductClass(Enum):
    GPU = "gpu"
    CPU = "cpu"
    ASIC = "asic"
    ROBOT = "robot"
    ROBOT_ARM = "robot_arm"
    MOBILE_ROBOT = "mobile_robot"
    HUMANOID = "humanoid"
    ACTUATOR = "actuator"
    SERVO = "servo"
    MOTOR = "motor"
    GEAR_REDUCER = "gear_reducer"
    ENCODER = "encoder"
    CAMERA = "camera"
    LIDAR = "lidar"
    CONTROLLER = "controller"
    PLC = "plc"
    SBC = "sbc"
    JETSON = "jetson"
    PSU = "psu"
    BATTERY = "battery"
    CHARGER = "charger"
    SENSOR = "sensor"
    NETWORK_INTERFACE = "network_interface"
    PRINTER_3D = "3d_printer"
    CNC = "cnc"
    PCB = "pcb"
    CONNECTOR = "connector"
    IC = "ic"
    MOSFET = "mosfet"
    BEARING = "bearing"
    FAN = "fan"
    CABLE = "cable"
    TOOL = "tool"
    COMPONENT = "component"
    OTHER = "other"


class Condition(Enum):
    NEW = "new"
    OPEN_BOX = "open_box"
    REFURBISHED = "refurbished"
    USED_LIKE_NEW = "used_like_new"
    USED_GOOD = "used_good"
    USED_FAIR = "used_fair"
    USED_POOR = "used_poor"
    BROKEN = "broken"
    FOR_PARTS = "for_parts"
    UNKNOWN = "unknown"


class Scope(Enum):
    COMPLETE_UNIT = "complete_unit"
    PART = "part"
    ACCESSORY = "accessory"
    BUNDLE = "bundle"
    UNKNOWN = "unknown"


class PriceType(Enum):
    RETAIL_ASK = "retail_ask"
    MARKETPLACE_ASK = "marketplace_ask"
    AUCTION_CURRENT_BID = "auction_current_bid"
    AUCTION_HAMMER_CONFIRMED = "auction_hammer_confirmed"
    SOLD_PRICE_CONFIRMED = "sold_price_confirmed"
    DEALER_BID = "dealer_bid"
    DEALER_EXCHANGE = "dealer_exchange"
    MANUFACTURER_LIST = "manufacturer_list"


class RelationType(Enum):
    VARIANT_OF = "VARIANT_OF"
    CONTAINS = "CONTAINS"
    COMPATIBLE_WITH = "COMPATIBLE_WITH"
    INCOMPATIBLE_WITH = "INCOMPATIBLE_WITH"
    REQUIRES = "REQUIRES"
    OPTIONALLY_USES = "OPTIONALLY_USES"
    REPLACES = "REPLACES"
    REPLACED_BY = "REPLACED_BY"
    SUPERSEDES = "SUPERSEDES"
    ALTERNATIVE_TO = "ALTERNATIVE_TO"
    MOUNTS_TO = "MOUNTS_TO"
    CONNECTS_TO = "CONNECTS_TO"
    CONTROLLED_BY = "CONTROLLED_BY"
    SENSES_WITH = "SENSES_WITH"
    POWERED_BY = "POWERED_BY"
    USES_PROTOCOL = "USES_PROTOCOL"
    HAS_INTERFACE = "HAS_INTERFACE"
    HAS_FIRMWARE = "HAS_FIRMWARE"
    SAME_AS = "SAME_AS"
    POSSIBLE_SAME_AS = "POSSIBLE_SAME_AS"


class LifecycleEventType(Enum):
    ANNOUNCED = "ANNOUNCED"
    RELEASED = "RELEASED"
    NEW_VARIANT = "NEW_VARIANT"
    FIRMWARE_RELEASED = "FIRMWARE_RELEASED"
    DISCONTINUED = "DISCONTINUED"
    SUPPORT_ENDED = "SUPPORT_ENDED"
    SUCCESSOR_DECLARED = "SUCCESSOR_DECLARED"
    PART_SUPERSEDED = "PART_SUPERSEDED"
    RESTOCKED = "RESTOCKED"
    STOCK_OUT = "STOCK_OUT"


class MarketEventType(Enum):
    LISTING_APPEARED = "LISTING_APPEARED"
    PRICE_CHANGED = "PRICE_CHANGED"
    AVAILABILITY_CHANGED = "AVAILABILITY_CHANGED"
    DISAPPEARED = "DISAPPEARED"
    REAPPEARED = "REAPPEARED"
    SOLD_CONFIRMED = "SOLD_CONFIRMED"
    STOCK_CHANGED = "STOCK_CHANGED"


class TruthClass(Enum):
    DECLARED = "declared"
    OBSERVED = "observed"
    INFERRED = "inferred"


class AccessStatus(Enum):
    OPEN = "open"
    APPROVED = "approved"
    TERMS_REVIEW = "terms_review"
    PERMISSION_REQUIRED = "permission_required"
    BLOCKED = "blocked"
