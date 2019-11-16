import json
import requests

def has_many(method_name, cls, column_name, single=False):
    class newCls:
        def __getattribute__(self, name):
            if name == method_name:
                # Get association ids in reverse order, because Airtable’s UI and API
                # sort associations in opposite directions. We want to match the UI.

                ids = getattr(self, column_name, []).reverse()
                if not single:
                    return cls.find_many(ids)
                else:
                    return cls.find(ids[0]) if ids[0] else None

                self.__getattribute__( name)

        def __setattr__(self, name, value):
            if name == method_name:
                self.fields[column_name] = [id for id in value].reverse()
            else:
                self.__setattr__(self, name, value)

def belongs_to(method_name, cls, column_name):
    has_many(method_name, cls, column_name, single=True)

def has_one(method_name, cls, column_name):
    belongs_to(method_name, cls, column_name)

def config(api_key, base_key, table_name):
    airtable_headers = {
        "Authorization": "Bearer {}".format(api_key),
        "User-Agent": "Airrecord/#{Airrecord::VERSION}",
        "X-API-VERSION": "0.1.0",
    }

    class Table:
        self.clients = {}
        self.api_key = ''
        self.base_key = ''
        self.table_name = ''

        def __init__(fields, id=None, created_at=None):
            self.id = id
            self.created_at = created_at
            self.fields = fields

        def handle_error(self, status, error):
           if isinstance(dict):
             raise Exception("HTTP {}: {}: {}".format(status, error['error']["type"], error['error']['message']))
           else:
             raise Exception("HTTP {}: Communication error: {}".format(status, error))


        @classmethod
        def find(cls, id):
            response = request.get("/v0/#{base_key}/#{client.escape(table_name)}/#{id}")
            parsed_response = response.json()

            if response:
                return cls.new(parsed_response["fields"], id=id)
            else:
                client.handle_error(response.status, parsed_response)

        @classmethod
        def find_many(cls, ids):
            if len(ids) == 0:
                return []

            or_args = ["RECORD_ID() = '{}'".format(id) for id in ids].join(",")
            formula = "OR({})".format(or_args)

            cls.all(filter=formula) #.sort_by { |record| or_args.index(record.id) }

        @classmethod
        def create(cls, fields):
            record = cls(fields)
            record.save

        @classmethod
        def all(cls, filter=None, sort=None, view=None, offset=None, paginate=True, fields=None, max_records=None, page_size=None):
            options = {}
            if filter:
                options['filterByFormula'] = filter
            if sort:
                options['sort'] = sort.map { |field, direction| { field: field.to_s, direction: direction }}
            if view:
                options['view'] = view
            if offset:
                options['offset'] = offset
            if fields:
                options['fields'] = fields
            if max_records:
                options['maxRecords'] = max_records
            if page_size:
                options['pageSize'] = page_size

            path = "https://api.airtable.com/v0/#{base_key}/#{client.escape(table_name)}"
            response = requests.get(path, options)

            if response:
                parsed_response = response.json()
                records = parsed_response["records"]
                records = [cls(record["fields"], id=record["id"], created_at=record["createdTime"]) for record in records]

                if paginate && parsed_response["offset"]:
                    records.append(records(filter=filter, sort=sort, view=view, paginate=paginate, fields=fields, offset=parsed_response["offset"], max_records=max_records, page_size=page_size))

                return records
            else:
                client.handle_error(response.status, parsed_response)


        def is_new_record(self):
           !id

        def getattr(self, key):
            if key in self.fields:
                return fields[key]

            self.getattr(self, key)

        def setattr(self, key, value):

    #     def []=(key, value)
    #       validate_key(key)
    #       return if fields[key] == value # no-op
    #       @updated_keys << key
    #       fields[key] = value
    #     end

        def create(self):
            if not is_new_record():
                raise Exception("Record already exists (record has an id)")

           body = { 'fields': self.fields }.to_json
           response = requests.post("/v0/#{self.class.base_key}/#{client.escape(self.class.table_name)}", body, { 'Content-Type' => 'application/json' })
           parsed_response = response.json()

           if response:
             self.id = parsed_response["id"]
             self.created_at = parsed_response["createdTime"]
             self.fields = parsed_response["fields"]
           else:
             self.handle_error(response.status, parsed_response)

        def save(self):
            if self.is_new_record():
                return self.create()

            if len(self.updated_keys) == 0:
                return True

            # To avoid trying to update computed fields we *always* use PATCH
            body = {
                fields: { key: self.fields[key] for key in self.updated_keys }
            }.to_json

            response = requests.patch("/v0/#{self.class.base_key}/#{client.escape(self.class.table_name)}/#{self.id}", body, { 'Content-Type' => 'application/json' })
            parsed_response = response.json()

            if response:
                self.fields = parsed_response["fields"]
            else:
                self.handle_error(response.status, parsed_response)

        def destroy(self):
           if is_new_record():
               raise Exception("Unable to destroy new record")

           response = requests.delete("/v0/#{self.class.base_key}/#{client.escape(self.class.table_name)}/#{self.id}")
           parsed_response = response.json()

           if response:
             return True
           else:
             self.handle_error(response.status, parsed_response)

    #     def ==(other)
    #       self.class == other.class &&
    #         serializable_fields == other.serializable_fields
    #     end


    #     def fields=(fields)
    #       @updated_keys = []
    #       @fields = fields
    #     end

    #     def created_at=(created_at)
    #       return unless created_at
    #       @created_at = Time.parse(created_at)
    #     end
