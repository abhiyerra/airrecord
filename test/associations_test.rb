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
    brew = Brew.new("Name" => "Hot")
    stub_post_request(brew, table: Brew)
    stubbed_brew_fields = brew.create.merge("id" => brew.id)

    tea.brews = [brew]

    stub_request([stubbed_brew_fields], table: Brew)
    assert_equal 1, tea.brews.size
    assert_kind_of Airrecord::Table, tea.brews.first
    assert_equal tea.brews.first.id, brew.id
  end
end
