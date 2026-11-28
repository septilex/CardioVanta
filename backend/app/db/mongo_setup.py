"""Idempotent Mongo validators/indexes. Run before serving feedback writes (replica set required)."""
from backend.app.db import mongo

EVENTS = "feedback_events"
FEEDBACK_SCHEMA = {
    "bsonType": "object", "additionalProperties": False,
    "required": ["helpful", "section", "model_version", "created_at", "updated_at", "edit_token_hash", "metadata"],
    "properties": {
        "_id": {"bsonType": "objectId"}, "helpful": {"bsonType": "bool"},
        "section": {"enum": ["summary", "why", "audit"]},
        "model_version": {"bsonType": "string", "pattern": r"^\d+\.\d+\.\d+$", "maxLength": 20},
        "created_at": {"bsonType": "date"}, "updated_at": {"bsonType": "date"},
        "edit_token_hash": {"bsonType": "string", "pattern": "^[a-f0-9]{64}$"},
        "metadata": {"bsonType": "object", "additionalProperties": False,
                     "required": ["surface", "schema_version"], "properties": {
                         "surface": {"enum": ["assessment"]}, "schema_version": {"enum": [1]}}},
    },
}
EVENT_SCHEMA = {
    "bsonType": "object", "additionalProperties": False,
    "required": ["feedback_id", "action", "fields", "created_at"],
    "properties": {
        "_id": {"bsonType": "objectId"}, "feedback_id": {"bsonType": "objectId"},
        "action": {"enum": ["created", "updated"]}, "created_at": {"bsonType": "date"},
        "fields": {"bsonType": "array", "maxItems": 2, "uniqueItems": True,
                   "items": {"enum": ["helpful", "section"]}},
    },
}


def setup(cfg=None):
    db = mongo.collection(cfg).database
    for name, schema in ((mongo.COLLECTION, FEEDBACK_SCHEMA), (EVENTS, EVENT_SCHEMA)):
        if name not in db.list_collection_names():
            db.create_collection(name)
        if name == mongo.COLLECTION:
            # Existing valid feedback gains bounded non-sensitive metadata before strict validation.
            db[name].update_many({"metadata": {"$exists": False}}, {"$set": {"metadata": {"surface": "assessment", "schema_version": 1}}})
            invalid = db[name].count_documents({"$nor": [{"$jsonSchema": schema}]})
            if invalid:
                raise RuntimeError("Existing feedback violates schema; review documents before enabling strict validation.")
        db.command("collMod", name, validator={"$jsonSchema": schema}, validationLevel="strict", validationAction="error")
    db[mongo.COLLECTION].create_index([("section", 1), ("created_at", -1)], name="feedback_section_created")
    db[mongo.COLLECTION].create_index([("model_version", 1), ("created_at", -1)], name="feedback_version_created")
    db[EVENTS].create_index([("feedback_id", 1), ("created_at", -1)], name="events_parent_created")


if __name__ == "__main__":
    setup()
    print("MongoDB validators and indexes are ready.")
