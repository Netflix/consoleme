import React, { Component } from 'react'
import _ from 'lodash'

import ReactDOM from 'react-dom'
import DataTable from 'react-data-table-component'
import { Input } from 'semantic-ui-react'
import { sendRequestCommon } from '../helpers/utils'

function maybeParseJsonString (str) {
  try {
    return JSON.parse(str)
  } catch (e) {
    return str
  }
}

function ExpandNestedJson (data) {
  const keys = Object.keys(data)
  keys.forEach(function (item, index) {
    data[item] = maybeParseJsonString(data[item])
  })
  return JSON.stringify(data, null, 2)
}

const ExpandedComponent = ({ data }) => (
  <div>
    <pre>{ExpandNestedJson(data)}</pre>
  </div>
)

class ConsoleMeDataTable extends Component {
  constructor (props) {
    super(props)
    this.state = {
      configEndpoint: props.configEndpoint,
      data: [],
      filteredData: [],
      q: '',
      loading: false,
      totalRows: 1000,
      perPage: 10,
      tableConfig: {
        expandableRows: true,
        expandOnRowClicked: true,
        pagination: true,
        highlightOnHover: true,
        striped: true,
        subHeader: true,
        filterColumns: true,
        tableName: '',
        sortable: false,
        grow: 3,
        wrap: true,
        dataEndpoint: '',
        desiredColumns: [],
        serverSideFiltering: true
      },
      filters: {},
      columns: []
    }
    this.filterColumn = this.filterColumn.bind(this)
    this.genColumns = this.genColumns.bind(this)
    this.filterColumn = _.debounce(this.filterColumn, 300, { leading: false, trailing: true })
  }

  generateCell (row, item) {
    if (item.cell.type === 'href') {
      let href = item.cell.href
      let name = item.cell.name
      const hrefReplacements = href.match(/\{(.*)\}/)
      const nameReplacements = name.match(/\{(.*)\}/)
      hrefReplacements.forEach(function (item, index) {
        try {
          const matches = href.matchAll(/\{(.*?)\}/g)
          for (const match of matches) {
            href = href.replace(match[0], eval(match[1]))
          }
        } catch (e) {}
      })

      nameReplacements.forEach(function (item, index) {
        try {
          const matches = name.matchAll(/\{(.*?)\}/g)
          for (const match of matches) {
            name = name.replace(match[0], eval(match[1]))
          }
        } catch (e) {}
      })

      return (
        <a href={href} target="_blank" rel="noopener noreferrer">
          {name}
        </a>
      )
    }
  }

  filterColumnServerSide (event, filters) {
    const { tableConfig } = this.state
    const firstColumnName = tableConfig.desiredColumns[0].selector;
    (async () => {
      const data = await sendRequestCommon({ filters: filters }, tableConfig.dataEndpoint)
      // Hacky bypass of this issue: https://github.com/jbetancur/react-data-table-component/issues/628
      if (data.length === 0) {
        data.push({
          [firstColumnName]:
            'There are no records to display. Please revise your filters.'
        })
      }
      this.setState({ filteredData: data, limit: tableConfig.totalRows, loading: false })
    })()
  }

  filterColumn (event) {
    this.setState({ loading: true })
    const { tableConfig } = this.state
    let filters = this.state.filters

    filters[event.target.name] = event.target.value
    this.setState({ filters: filters })
    if (tableConfig.serverSideFiltering) {
      this.filterColumnServerSide(event, filters)
    } else {
      this.filterColumnClientSide(event, filters)
    }
  }

  filterColumnClientSide (event, filters) {
    let { data, tableConfig } = this.state
    const firstColumnName = tableConfig.desiredColumns[0].selector
    let filteredData = data
    filteredData = filteredData.filter(function (item) {
      for (let key in filters) {
        let re = filters[key]
        try {
          re = new RegExp(filters[key], 'g')
        } catch (e) {
          // Invalid Regex. Ignore
        }

        if (
          item[key] === undefined ||
          item[key] === '' ||
          !String(item[key]).match(re)
        ) { return false }
      }
      return true
    })

    // Hacky bypass of this issue: https://github.com/jbetancur/react-data-table-component/issues/628
    if (filteredData.length === 0) {
      filteredData.push({
        [firstColumnName]:
          'There are no records to display. Please revise your filters.'
      })
    }
    this.setState({ filteredData: filteredData, loading: false })
  }

  genColumns (tableConfig) {
    let columns = []
    let filters = this.state.filters

    tableConfig.desiredColumns.forEach(
      function (item, index) {
        let name = item.name
        if (tableConfig.filterColumns) {
          name = (
            <Input
              name={item.selector}
              placeholder={'Search ' + item.name}
              onChange={(event) => {
                event.persist()
                this.filterColumn(event)
              }}
              value={'' || filters[item.name]}
            />
          )
        }
        let column = {
          name: name,
          selector: item.selector,
          sortable: tableConfig.sortable,
          grow: tableConfig.grow,
          wrap: tableConfig.wrap
        }

        if (item.cell) {
          // We're evaling the Cell configuration provided by ConsoleMe, and not untrusted user input.
          column.cell = row => this.generateCell(row, item)
        }
        columns.push(column)
      }.bind(this)
    )
    this.setState({ columns: columns })
  }

  async componentDidMount () {
    this.setState({ loading: true })
    let data = []
    const configRequest = await fetch(this.state.configEndpoint)
    const tableConfig = await configRequest.json()
    this.setState({ tableConfig: tableConfig })

    if (tableConfig.dataEndpoint) {
      const data = await sendRequestCommon({ limit: tableConfig.totalRows }, tableConfig.dataEndpoint)
      this.setState({ data: data })
      // Todo: Support filtering based on query parameters
      this.setState({ filteredData: data })
    }
    if (data) {
      this.genColumns(tableConfig)
    }
    this.setState({ loading: false })
  }

  render () {
    const { loading, filteredData, tableConfig, columns } = this.state
    return (
      <div>
        <DataTable
          title={tableConfig.tableName}
          columns={columns}
          data={filteredData}
          progressPending={loading}
          expandableRows={tableConfig.expandableRows}
          expandOnRowClicked={tableConfig.expandOnRowClicked}
          pagination={tableConfig.pagination}
          highlightOnHover={tableConfig.highlightOnHover}
          striped={tableConfig.striped}
          subHeader={tableConfig.subHeader}
          expandableRowsComponent={<ExpandedComponent />}
          persistTableHead={true}
        />
      </div>
    )
  }
}

export function renderDataTable (configEndpoint) {
  ReactDOM.render(
    <ConsoleMeDataTable configEndpoint={configEndpoint} />,
    document.getElementById('datatable')
  )
}

export default ConsoleMeDataTable
