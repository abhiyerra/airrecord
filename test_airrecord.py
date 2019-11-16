require 'test_helper'

class AirrecordTest < Minitest::Test
  def test_set_api_key
    Airrecord.api_key = "walrus"
    assert_equal "walrus", Airrecord.api_key
  end
end
require 'test_helper'

class Tea < Airrecord::Table
  self.api_key = "key1"
  self.base_key = "app1"
  self.table_name = "Teas"

  has_many :brews, class: "Brew", column: "Brews"
  has_one :pot, class: "Teapot", column: "Teapot"
end

class Brew < Airrecord::Table
  self.api_key = "key1"
  self.base_key = "app1"
  self.table_name = "Brews"

  belongs_to :tea, class: "Tea", column: "Tea"
end

class Teapot < Airrecord::Table
  self.api_key = "key1"
  self.base_key = "app1"
  self.table_name = "Teapots"

  belongs_to :tea, class: "Tea", column: "Tea"
end


class AssociationsTest < MiniTest::Test
  def setup
    @stubs = Faraday::Adapter::Test::Stubs.new
    Tea.client.connection = Faraday.new { |builder|
      builder.adapter :test, @stubs
    }
  end

  def test_has_many_associations
    tea = Tea.new("Name" => "Dong Ding", "Brews" => ["rec2", "rec1"])

    brews = [
      { "id" => "rec2", "Name" => "Good brew" },
      { "id" => "rec1", "Name" => "Decent brew" }
    ]
    stub_request(brews, table: Brew)

    assert_equal 2, tea.brews.size
    assert_kind_of Airrecord::Table, tea.brews.first
    assert_equal "rec1", tea.brews.first.id
  end

  def test_has_many_handles_empty_associations
    tea = Tea.new("Name" => "Gunpowder")
    stub_request([{ "id" => "brew1", "Name" => "unrelated"  }], table: Brew)
    assert_equal 0, tea.brews.size
  end

  def test_belongs_to
    brew = Brew.new("Name" => "Good Brew", "Tea" => ["rec1"])
    tea = Tea.new("Name" => "Dong Ding", "Brews" => ["rec2"])
    stub_find_request(tea, table: Tea, id: "rec1")

    assert_equal "rec1", brew.tea.id
  end

  def test_has_one
    tea = Tea.new("id" => "rec1", "Name" => "Sencha", "Teapot" => ["rec3"])
    pot = Teapot.new("Name" => "Cast Iron", "Tea" => ["rec1"])
    stub_find_request(pot, table: Teapot, id: "rec3")

    assert_equal "rec3", tea.pot.id
  end

  def test_has_one_handles_empty_associations
    pot = Teapot.new("Name" => "Ceramic")

    assert_nil pot.tea
  end

  def test_build_association_from_strings
    tea = Tea.new({"Name" => "Jingning", "Brews" => ["rec2", "rec1"]})
    stub_post_request(tea, table: Tea)

    tea.create

    stub_request([{ id: "rec2" }, { id: "rec1" }], table: Brew)
    assert_equal 2, tea.brews.count
  end

  def test_build_belongs_to_association_from_setter
    tea = Tea.new({"Name" => "Jingning", "Brews" => []}, id: "rec1")
    brew = Brew.new("Name" => "greeaat")
    brew.tea = tea
    stub_post_request(brew, table: Brew)

    brew.create

    stub_find_request(tea, table: Tea, id: "rec1")
    assert_equal tea.id, brew.tea.id
  end

  def test_build_has_many_association_from_setter
    tea = Tea.new("Name" => "Earl Grey")
    brews = %w[Perfect Meh].each_with_object([]) do |name, memo|
      brew = Brew.new("Name" => name)
      stub_post_request(brew, table: Brew)
      brew.create
      memo << brew
    end

    tea.brews = brews

    brew_fields = brews.map { |brew| brew.fields.merge("id" => brew.id) }
    stub_request(brew_fields, table: Brew)

    assert_equal 2, tea.brews.size
    assert_kind_of Airrecord::Table, tea.brews.first
    assert_equal tea.brews.first.id, brews.first.id
  end
end
require 'test_helper'
require 'airrecord/faraday_rate_limiter'

class FaradayRateLimiterTest < Minitest::Test
  def setup
    @stubs = Faraday::Adapter::Test::Stubs.new
    @rps = 5
    @sleeps = []
    @connection = Faraday.new { |builder|
      builder.request :airrecord_rate_limiter,
        requests_per_second: @rps,
        sleeper: ->(s) { @sleeps << s }

      builder.adapter :test, @stubs
    }

    @stubs.get("/whatever") do |env|
      [200, {}, "walrus"]
    end
  end

  def teardown
    @connection.app.clear
  end

  def test_passes_through_single_request
    @connection.get("/whatever")
    assert_predicate @sleeps, :empty?
  end

  def test_sleeps_on_the_rps_plus_oneth_request
    @rps.times do
      @connection.get("/whatever")
    end

    assert_predicate @sleeps, :empty?

    @connection.get("/whatever")

    assert_equal 1, @sleeps.size
    assert @sleeps.first > 0.9
  end
end
require 'test_helper'

class QueryStringTest < Minitest::Test
  def setup
    @params = { maxRecords: 50, view: "Master" }
    @query = "maxRecords=3&pageSize=1&sort%5B0%5D%5Bfield%5D=Quality&sort%5B0%5D%5Bdirection%5D=asc"
    @qs = Airrecord::QueryString
  end

  def test_encoding_simple_params_matches_faraday
    expected = Faraday::NestedParamsEncoder.encode(@params)
    result = @qs.encode(@params)

    assert_equal(result, expected)
  end

  def test_decode_matches_faraday
    assert_equal(
      Faraday::NestedParamsEncoder.decode(@query),
      @qs.decode(@query),
    )
  end

  def test_encoding_arrays_uses_indices
    params = @params.merge(fields: %w[Quality Price])

    expected = "maxRecords=50&view=Master&fields%5B0%5D=Quality&fields%5B1%5D=Price"
    result = @qs.encode(params)

    assert_equal(result, expected)
  end

  def test_encoding_arrays_of_objects
    params = { sort: [
      { field: 'Quality', direction: 'desc' },
      { field: 'Price', direction: 'asc' }
    ]}

    expected = "sort%5B0%5D%5Bfield%5D=Quality&sort%5B0%5D%5Bdirection%5D=desc&sort%5B1%5D%5Bfield%5D=Price&sort%5B1%5D%5Bdirection%5D=asc"
    result = @qs.encode(params)

    assert_equal(result, expected)
  end

  def test_params_fuzzing
    params = {
      "an explicit nil" => nil,
      horror: [1, 2, [{ mic: "check" }, { one: "two" }]],
      view: "A name with spaces",
    }

    expected = {
      "an explicit nil" => "",
      "horror" => ["1", "2", [{ "mic" => "check" }, { "one" => "two" }]],
      "view" => "A name with spaces",
    }
    result = Faraday::NestedParamsEncoder.decode(@qs.encode(params))

    assert_equal(result, expected)
  end

  def test_escaping_one_string
    assert_equal(@qs.escape("test string"), "test%20string")
  end

  def test_escaping_many_strings
    strings = ['test', 'string']
    assert_equal(@qs.escape(*strings), 'teststring')
  end
end
require 'securerandom'
require 'test_helper'

class Walrus < Airrecord::Table
  self.base_key = 'app1'
  self.table_name = 'walruses'

  has_many :feet, class: 'Foot', column: 'Feet'
end

class Foot < Airrecord::Table
  self.base_key = 'app1'
  self.table_name = 'foot'

  belongs_to :walrus, class: 'Walrus', column: 'Walrus'
end

class TableTest < Minitest::Test
  def setup
    Airrecord.api_key = "key2"
    @table = Airrecord.table("key1", "app1", "table1")

    @stubs = Faraday::Adapter::Test::Stubs.new
    @table.client.connection = Faraday.new { |builder|
      builder.adapter :test, @stubs
    }

    stub_request([{"Name" => "omg", "Notes" => "hello world"}, {"Name" => "more", "Notes" => "walrus"}])
  end

  def test_table_overrides_key
    assert_equal "key1", @table.api_key
  end

  def test_walrus_uses_default_key
    assert_equal "key2", Walrus.api_key
  end

  def test_retrieve_records
    assert_instance_of Array, @table.records
  end

  def test_different_clients_with_different_api_keys
    table1 = Airrecord.table("key1", "app1", "unknown")
    table2 = Airrecord.table("key2", "app2", "unknown")

    refute_equal table1.client, table2.client
  end

  def test_filter_records
    stub_request([{"Name" => "yes"}, {"Name" => "no"}])

    records = @table.records(filter: "Name")
    assert_equal "yes", records[0]["Name"]
  end

  def test_sort_records
    stub_request([{"Name" => "a"}, {"Name" => "b"}])

    records = @table.records(sort: { "Name" => 'asc' })
    assert_equal "a", records[0]["Name"]
    assert_equal "b", records[1]["Name"]
  end

  def test_view_records
    stub_request([{"Name" => "a"}, {"Name" => "a"}])

    records = @table.records(view: 'A')
    assert_equal "a", records[0]["Name"]
    assert_equal "a", records[1]["Name"]
  end

  def test_follow_pagination_by_default
    stub_request([{"Name" => "1"}, {"Name" => "2"}], offset: 'dasfuhiu')
    stub_request([{"Name" => "3"}, {"Name" => "4"}], offset: 'odjafio', clear: false)
    stub_request([{"Name" => "5"}, {"Name" => "6"}], clear: false)

    records = @table.records
    assert_equal 6, records.size
  end

  def test_dont_follow_pagination_if_disabled
    stub_request([{"Name" => "1"}, {"Name" => "2"}], offset: 'dasfuhiu')
    stub_request([{"Name" => "3"}, {"Name" => "4"}], offset: 'odjafio', clear: false)
    stub_request([{"Name" => "5"}, {"Name" => "6"}], clear: false)

    records = @table.records(paginate: false)
    assert_equal 2, records.size
  end

  def test_index_by_normalized_name
    assert_equal "omg", first_record["Name"]
  end

  def test_index_by_column_name
    assert_equal "omg", first_record["Name"]
  end

  def test_id
    assert_instance_of String, first_record.id
  end

  def test_created_at
    assert_instance_of Time, first_record.created_at
  end

  def test_error_response
    table = Airrecord.table("key1", "app1", "unknown")

    stub_error_request(type: "TABLE_NOT_FOUND", message: "Could not find table", table: table)

    assert_raises Airrecord::Error do
      table.records
    end
  end

  def test_change_value
    record = first_record
    record["Name"] = "testest"
    assert_equal "testest", record["Name"]
  end

  def test_change_value_on_column_name
    record = first_record
    record["Name"] = "testest"
    assert_equal "testest", record["Name"]
  end

  def test_change_value_and_update
    record = first_record

    record["Name"] = "new_name"
    stub_patch_request(record, ["Name"])

    assert record.save
  end

  def test_change_value_then_save_again_should_noop
    record = first_record

    record["Name"] = "new_name"
    stub_patch_request(record, ["Name"])

    assert record.save
    assert record.save
  end

  def test_change_value_with_symbol_raises_error
    assert_raises Airrecord::Error do
      first_record[:Name] = "new_name"
    end
  end

  def test_access_value_with_symbol_raises_error
    assert_raises Airrecord::Error do
      first_record[:Name]
    end
  end

  def test_updates_fields_to_newest_values_after_update
    record = first_record

    record["Name"] = "new_name"
    stub_patch_request(record, ["Name"], return_body: { fields: record.fields.merge("Notes" => "new animal") })

    assert record.save
    assert_equal "new_name", record["Name"]
    assert_equal "new animal", record["Notes"]
  end

  def test_update_failure
    record = first_record

    record["Name"] = "new_name"
    stub_patch_request(record, ["Name"], return_body: { error: { type: "oh noes", message: 'yes' } }, status: 401)

    assert_raises Airrecord::Error do
      record.save
    end
  end

  def test_update_failure_then_succeed
    record = first_record

    record["Name"] = "new_name"
    stub_patch_request(record, ["Name"], return_body: { error: { type: "oh noes", message: 'yes' } }, status: 401)

    assert_raises Airrecord::Error do
      record.save
    end

    stub_patch_request(record, ["Name"])
    assert record.save
  end

  def test_update_creates_if_new_record
    record = @table.new("Name" => "omg")

    stub_post_request(record)

    assert record.save
  end

  def test_existing_record_is_not_new
    refute first_record.new_record?
  end

  def test_build_new_record
    record = @table.new("Name" => "omg")

    refute record.id
    refute record.created_at
    assert record.new_record?
  end

  def test_create_new_record
    record = @table.new("Name" => "omg")

    stub_post_request(record)

    assert record.create
  end

  def test_create_existing_record_fails
    record = @table.new("Name" => "omg")

    stub_post_request(record)

    assert record.create

    assert_raises Airrecord::Error do
      record.create
    end
  end

  def test_create_handles_error
    record = @table.new("Name" => "omg")

    stub_post_request(record, status: 401, return_body: { error: { type: "omg", message: "wow" }})

    assert_raises Airrecord::Error do
      record.create
    end
  end

  def test_class_level_create
    record = @table.new("Name" => "omg")

    stub_post_request(record)

    record = @table.create(record.fields)
    assert record.id
  end

  def test_class_level_create_handles_error
    record = @table.new("Name" => "omg")

    stub_post_request(record, status: 401, return_body: { error: { type: "omg", message: "wow" }})

    assert_raises Airrecord::Error do
      @table.create record.fields
    end
  end


  def test_find
    record = @table.new("Name" => "walrus")

    stub_find_request(record, id: "iodfajsofja")

    record = @table.find("iodfajsofja")
    assert_equal "walrus", record["Name"]
    assert_equal "iodfajsofja", record.id
  end

  def test_find_handles_error
    stub_find_request(nil, return_body: { error: { type: "not found", message: "not found" } }, id: "noep", status: 404)

    assert_raises Airrecord::Error do
      @table.find("noep")
    end
  end

  def test_find_many
    ids = %w[rec1 rec2 rec3]
    assert_instance_of Array, @table.find_many(ids)
  end

  def test_find_many_makes_no_network_call_when_ids_are_empty
    stub_request([], status: 500)

    assert_equal([], @table.find_many([]))
  end

  def test_destroy_new_record_fails
    record = @table.new("Name" => "walrus")

    assert_raises Airrecord::Error do
      record.destroy
    end
  end

  def test_destroy_record
    record = first_record
    stub_delete_request(record.id)
    assert record.destroy
  end

  def test_fail_destroy_record
    record = first_record
    stub_delete_request(record.id, status: 404, response_body: { error: { type: "not found", message: "whatever" } }.to_json)

    assert_raises Airrecord::Error do
      record.destroy
    end
  end

  def test_error_handles_errors_without_body
    record = first_record

    stub_delete_request(record.id, status: 500)

    assert_raises Airrecord::Error do
      record.destroy
    end
  end

  def test_dates_are_not_type_casted
    stub_request([{"Name" => "omg", "Created" => Time.now.to_s}])

    record = first_record
    assert_instance_of String, record["Created"]
  end

  def test_comparison
    alpha = @table.new("Name" => "Name", "Created" => Time.at(0))
    beta = @table.new("Name" => "Name", "Created" => Time.at(0))

    assert_equal alpha, beta
  end

  def test_comparison_different_classes
    alpha = @table.new("Name" => "Name", "Created" => Time.at(0))
    beta = Walrus.new("Name" => "Name", "Created" => Time.at(0))

    refute_equal alpha, beta
  end

  def test_association_accepts_non_enumerable
    walrus = Walrus.new("Name" => "Wally")
    foot = Foot.new("Name" => "FrontRight", "walrus" => walrus)

    foot.serializable_fields
  end

  def test_dont_update_if_equal
    walrus = Walrus.new("Name" => "Wally")
    walrus["Name"] = "Wally"
    assert walrus.updated_keys.empty?
  end

  def test_equivalent_records_are_eql?
    walrus1 = Walrus.new("Name" => "Wally")
    walrus2 = Walrus.new("Name" => "Wally")

    assert walrus1.eql? walrus2
  end

  def test_non_equivalent_records_fail_eql?
    walrus1 = Walrus.new("Name" => "Wally")
    walrus2 = Walrus.new("Name" => "Wally2")

    assert !walrus1.eql?(walrus2)
  end

  def test_equivalent_hash_equality
    walrus1 = Walrus.new("Name" => "Wally")
    walrus2 = Walrus.new("Name" => "Wally")

    assert_equal walrus1.hash, walrus2.hash
  end

  def test_non_equivalent_hash_inequality
    walrus1 = Walrus.new("Name" => "Wally")
    walrus2 = Walrus.new("Name" => "Wally2")

    assert walrus1.hash != walrus2.hash
  end
end
$LOAD_PATH.unshift File.expand_path('../../lib', __FILE__)
require 'airrecord'
require 'byebug'
require 'securerandom'
require 'minitest/autorun'

class Minitest::Test
  def stub_delete_request(id, table: @table, status: 202, response_body: "")
    @stubs.delete("/v0/#{@table.base_key}/#{@table.table_name}/#{id}") do |env|
      [status, {}, response_body]
    end
  end

  def stub_post_request(record, table: @table, status: 200, headers: {}, return_body: nil)
    return_body ||= {
      id: SecureRandom.hex(16),
      fields: record.serializable_fields,
      createdTime: Time.now,
    }
    return_body = return_body.to_json

    request_body = {
      fields: record.serializable_fields,
    }.to_json

    @stubs.post("/v0/#{table.base_key}/#{table.table_name}", request_body) do |env|
      [status, headers, return_body]
    end
  end

  def stub_patch_request(record, updated_keys, table: @table, status: 200, headers: {}, return_body: nil)
    return_body ||= { fields: record.fields }
    return_body = return_body.to_json

    request_body = {
      fields: Hash[updated_keys.map { |key|
        [key, record.fields[key]]
      }]
    }.to_json
    @stubs.patch("/v0/#{@table.base_key}/#{@table.table_name}/#{record.id}", request_body) do |env|
      [status, headers, return_body]
    end
  end

  # TODO: Problem, can't stub on params.
  def stub_request(records, table: @table, status: 200, headers: {}, offset: nil, clear: true)
    @stubs.instance_variable_set(:@stack, {}) if clear

    body = {
      records: records.map { |record|
        {
          id: record["id"] || SecureRandom.hex(16),
          fields: record,
          createdTime: Time.now,
        }
      },
      offset: offset,
    }.to_json

    @stubs.get("/v0/#{table.base_key}/#{table.table_name}") do |env|
      [status, headers, body]
    end
  end

  def stub_find_request(record = nil, table: @table, status: 200, headers: {}, return_body: nil, id: nil)
    return_body ||= {
      id: id,
      fields: record.fields,
    }
    return_body = return_body.to_json

    id ||= record.id

    @stubs.get("/v0/#{table.base_key}/#{table.table_name}/#{id}") do |env|
      [status, headers, return_body]
    end
  end

  def stub_error_request(type:, message:, status: 401, headers: {}, table: @table)
    body = {
      error: {
        type: type,
        message: message,
      }
    }.to_json

    @stubs.get("/v0/#{table.base_key}/#{table.table_name}") do |env|
      [status, headers, body]
    end
  end

  def first_record
    @table.records.first
  end
end
