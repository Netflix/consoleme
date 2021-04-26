# UI Components

ConsoleMe's [UI](https://github.com/Netflix/consoleme/tree/master/ui) is built with yarn. It's currently a mixture of class components, and React Hooks. **We want to migrate all remaining Class components to functional React Hooks \(contributions welcome\).**

## **Primary Components**

### **ConsoleMe Datatable**

The ConsoleMe datatable is a primary component of ConsoleMe, and one of the most complex. It's used for the Policies view, Select Role view, and All Policy Requests view. 

The data table is invoked with a backend ConsoleMe route that provides a configuration for the data table. The configuration tells the data table what columns to render, where to fetch data, and how to handle filtering.

Here's an example configuration that might be provided by the backend:

```text
{
    "expandableRows":true, // enable expanding rows with more detail
    "dataEndpoint":"/api/v2/eligible_roles", // where to retrieve data for the table
    "sortable":false, // is this table sortable?
    "totalRows":1000, // used for limiting how many items we retrieve from the backend
    "rowsPerPage":50, // how many rows do we want to show?
    "serverSideFiltering":false, // the filtering is done from the backend if this is set to true
    "columns":[
        {
     "placeholder":"Account Name", // Placeholder for filter input
     "Key":"account_name", // key used to retrieve the data for this column
     "type":"input" // the type of this column
        },
        {
     "placeholder":"Account ID",
     "key":"account_id",
     "type":"input"
        },
        {
     "placeholder":"Role Name",
     "key":"role_name",
     "type":"link"
        },
        {
     "placeholder":"AWS Console Sign-In",
     "key":"redirect_uri",
     "type":"button",
     "icon":"sign-in",
     "content":"Sign-In",
     "onClick":{
       "action":"redirect"
     }
        }
    ]
}
```

Here's an example invocation of the DataTable with a configuration:

```text
// update the path to the component
import DataTable from "datatable/DataTableComponent"; 

<DataTable config={tableConfig} />
```

#### **Data Endpoint**

Once the configuration is given to the Datatable component. a useEffect hook in useDataTable  will retrieve  data from the backend through the dataEndpoint url in the table configuration JSON.

#### **Client/Server Side Filtering**

Once the data is pulled from the backend, depending on whether serverSideFiltering is true or not, it will decide when to retrieve the data. The  example above is configured to fetch only once from the backend, filtering would be done from the client side. 

For server-side filtering, the datatable would reach to the backend with the user's query. The backend would fetch, filter, and return a limited number of rows to the frontend to render.

#### **Query String Filtering**

The datatable also supports filtering from the query string. For example, if you want to filter items via the column account\_name, you can supply a query string such as **?account\_name=awsprod** to filter items by account\_name. You can also filter by hidden fields \(Fields that are provided in the JSON by the backend, but which are not displayed as columns to the end useR\).

#### **Supported Column Types**

The current datatable supports following column types:

* Dropdown
* Input
* Link
* Daterange
* Button
* Icon
* Basic Text

You can learn more about the existing column types, you can take a look at the file **DataTableColumnsComponent.js**

### **auth/ProtectedRoutes.js**

We have at least two types of routes that exist in ConsoleMe's UI. The first is for protected \(authenticated\) pages, and the other is for public pages \(Not Found, Login/Registration\). The pages that require authentication are protected by ProtectedRoutes which is used along with React Router. The component checks whether a session exists and also renders the required header and sidebar based on a configuration provided by the backend.

### **src/components/roles/SelectRoles.js**

SelectRoles.js  is the default landing page, and also the page that allows AWS Console login. This page shows the list of AWS IAM roles that the user is authorized to use, and allows the user to login to the AWS Console with limited permissions. This page heavily relies on the DataTable component which is explained later in this documentation.

### **src/components/selfservice/SelfService.js**

SelfService.js is the entry point to ConsoleMe's Self Service IAM wizard. Users can generate AWS permission requests  through this page. It's currently limited to generating permission requests for IAM roles. For example, a user can generate a permission that allows their application's IAM role to access an S3 bucket. 

The self service wizard is a 3-step wizard that makes it easy for users to request permissions without having to know the AWS permissions JSON syntax. The first step asks the user which application or role they would like to add extra permissions to. The second step allows the user to select a list of canned AWS services permissions \(This canned list is configurable. ConsoleMe ships with a set of sane default options\). There’s  also an “Other” section in the second step that allows users to specify other services that we haven’t carefully curated permissions for. The second step renders the components dynamically depending on a configuration provided by the backend \(see SelfServiceComponent.js\). 

The final step allows the user to submit permission requests along with giving them a final chance to update the permissions manually via a Monaco editor.

**This component has not been migrated to React Hooks**. **Contributions welcome.**

### **src/components/policy/PolicyEditor.js**

This component is heavily used by CIS employees and advanced end-users whenever they need to handle requests from customers or need to update permissions for roles.

This policy editor renders its content differently depending on which policy type \(inline, managed and assumed role\) is loaded for editing. The PolicyProvider is used for managing the global states for this editor along with other React Hooks depending on this provider which manages extra states for specific features separately.

Here is the diagram explaining how this component manages state and its related components**:**

![](https://lh6.googleusercontent.com/RqaPy1YNrzeK6vJeNZdgWEGXaq14WewYhcog1-fTr9fc7AV3F6NNuXX2_4kdvnZpZG-S4XVfx7w0mqFhzctyS2d_6dopDzMeDvpkDDz3V9Omtv4PEstZrsJWJoSGnVND6DyJuQfF)

\*\*\*\*

### **src/components/policy/hooks/PolicyProvider.js**

This is a provider that manages the global states and exports its states and helper functions to read/update the states.  ****This provider parses the current url for resource information and fetches its detail from the backend and stores its data into its reducer. 

This will later be used by other React Hooks that are being used by other components with different contexts, such as inline policies, managed policies, and more.

### **src/components/policy/hooks**

This directory contains the provider, reducers and hooks for the Policy Editor to manage its data and states. The followings are the hooks that will use the data from the provider along with extra states to provide complete state for specific features.

* **useInlinePolicy:** This hook provides the inline policy related states for the editor and is one of the most used hooks.
* **useManagedPolicy:** similar to the **useInlinePolicy** hook, this handles the state for managed policies on a given IAM role.
* **useAssumeRolePolicy:** This manages the states for a role's trust policy, and applicable updates.
* **useResourcePolicy:** This is a hook for resources, such as S3 buckets, SQS queues, and SNS topics. 
* **usePolicyTag:** This hook manages the tags for a given resource.

### **src/components/request/PolicyRequestReview.js**

**PolicyRequestReview.js** handles the policy review page, which is used to view, edit, approve, cancel,  reject, comment, or otherwise manage policy requests. ****

This component is fairly large and may require a breakdown. This component will render dynamically depending on the request types. This is a list of components used to render this request review page:

* InlinePolicyChangeComponent
* ManagedPolicyChangeComponent
* AssumeRolePolicyChangeComponent
* ResourceTagChangeComponent
* ResourcePolicyChangeComponent

**This component has not been migrated to React Hooks**. **Contributions welcome.**

