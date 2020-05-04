import _ from 'lodash';
import faker from 'faker';
import React, {Component} from 'react';
import {
    Button,
    Checkbox,
    Divider,
    Dropdown,
    Feed,
    Form,
    FormDropdown,
    Grid,
    Icon,
    Image,
    Input,
    Item,
    Label,
    List,
    Header,
    Message,
    Menu,
    Search,
    Segment,
    Select,
    Step,
    TextArea,
} from 'semantic-ui-react';


const initialState = {
    activeItem: 'all',
    isLoading: false,
    results: [],
    value: ''
};

const getResults = () =>
    _.times(5, () => ({
        title: faker.company.companyName(),
        description: faker.company.catchPhrase(),
        image: faker.internet.avatar(),
        price: faker.finance.amount(0, 100, 2, '$'),
    }));

const source = _.range(0, 3).reduce((memo) => {
    const name = faker.hacker.noun();

    // eslint-disable-next-line no-param-reassign
    memo[name] = {
        name,
        results: getResults(),
    };

    return memo
}, {});

const CatalogItems = () => (
    <Item.Group divided relaxed>
        <Item>
            <Item.Image as="a" href="/selfservice" size='tiny' src='/static/logos/nosunglasses/1.png' />
            <Item.Content>
                <Item.Header as='a'>Self-Service IAM Wizard</Item.Header>
                <Item.Meta>Description</Item.Meta>
                <Item.Description>
                    ConsoleMe’s Self-Service Wizard to request access to AWS services or resources.
                </Item.Description>
                <Item.Extra>
                    <Label size="tiny" color="blue">
                        <Icon name="tag" />
                        AWS
                    </Label>
                    <Label size="tiny" color="blue">
                        <Icon name="tag" />
                        IAM
                    </Label>
                    <Label size="tiny" color="blue">
                        <Icon name="tag" />
                        Role
                    </Label>
                    <Label size="tiny" color="blue">
                        <Icon name="tag" />
                        Permission
                    </Label>
                </Item.Extra>
            </Item.Content>
        </Item>
        <Item>
            <Item.Image as='a' hfre="https://go/honeybee" size='tiny' src='/static/logos/infrasec/Honeybee.png' />
            <Item.Content>
                <Item.Header as='a'>HoneyBee</Item.Header>
                <Item.Meta>Description</Item.Meta>
                <Item.Description>
                    Honeybee is an orchestration system for AWS Lambda that is focused on secure configuration assurance for AWS infrastructure resources across many AWS accounts.
                </Item.Description>
                <Item.Extra>
                    <Label size="tiny" color="blue">
                        <Icon name="tag" />
                        AWS
                    </Label>
                    <Label size="tiny" color="blue">
                        <Icon name="tag" />
                        Account
                    </Label>
                    <Label size="tiny" color="blue">
                        <Icon name="tag" />
                        IAM
                    </Label>
                    <Label size="tiny" color="blue">
                        <Icon name="tag" />
                        Role
                    </Label>
                    <Label size="tiny" color="blue">
                        <Icon name="tag" />
                        Permission
                    </Label>
                </Item.Extra>
            </Item.Content>
        </Item>
        <Item>
            <Item.Image size='tiny' src='/static/logos/sunglasses/1.png' />
            <Item.Content>
                <Item.Header as='a'>API Protect</Item.Header>
                <Item.Meta>Description</Item.Meta>
                <Item.Description>
                    API Protect is a set of AWS IAM managed policies that, when applied to an AWS IAM user or role, effectively restricts the use of credentials issued for that entity to only Netflix's network space.
                </Item.Description>
                <Item.Extra>
                    <Label size="tiny" color="blue">
                        <Icon name="tag" />
                        AWS
                    </Label>
                    <Label size="tiny" color="blue">
                        <Icon name="tag" />
                        IAM
                    </Label>
                    <Label size="tiny" color="blue">
                        <Icon name="tag" />
                        Role
                    </Label>
                    <Label size="tiny" color="blue">
                        <Icon name="tag" />
                        Network
                    </Label>
                    <Label size="tiny" color="blue">
                        <Icon name="tag" />
                        VPC
                    </Label>
                    <Label size="tiny" color="blue">
                        <Icon name="tag" />
                        Subnet
                    </Label>
                </Item.Extra>
            </Item.Content>
        </Item>
        <Item>
            <Item.Image size='tiny' src='/static/logos/sunglasses/3.png' />
            <Item.Content>
                <Item.Header as='a'>Role Protect</Item.Header>
                <Item.Meta>Description</Item.Meta>
                <Item.Description>
                    RoleProtect authorizes applications to make use of AWS IAM roles.
                </Item.Description>
                <Item.Extra>
                    <Label size="tiny" color="blue">
                        <Icon name="tag" />
                        AWS
                    </Label>
                    <Label size="tiny" color="blue">
                        <Icon name="tag" />
                        IAM
                    </Label>
                    <Label size="tiny" color="blue">
                        <Icon name="tag" />
                        Role
                    </Label>
                    <Label size="tiny" color="blue">
                        <Icon name="tag" />
                        Spinnaker
                    </Label>
                    <Label size="tiny" color="blue">
                        <Icon name="tag" />
                        Gandalf
                    </Label>
                </Item.Extra>
            </Item.Content>
        </Item>
        <Item>
            <Item.Image size='tiny' src='/static/logos/infrasec/MikeCloudNoGradientWithFace.png' />
            <Item.Content>
                <Item.Header as='a'>SWAG</Item.Header>
                <Item.Meta>Description</Item.Meta>
                <Item.Description>
                    SWAG serves as a centralized repository account (only AWS accounts) related information.
                </Item.Description>
                <Item.Extra>
                    <Label size="tiny" color="blue">
                        <Icon name="tag" />
                        AWS
                    </Label>
                    <Label size="tiny" color="blue">
                        <Icon name="tag" />
                        Account
                    </Label>
                    <Label size="tiny" color="blue">
                        <Icon name="tag" />
                        Metadata
                    </Label>
                </Item.Extra>
            </Item.Content>
        </Item>
        <Item>
            <Item.Image size='tiny' src='/static/logos/infrasec/MikeCloudNoGradientWithFace.png' />
            <Item.Content>
                <Item.Header as='a'>Otterbot</Item.Header>
                <Item.Meta>Description</Item.Meta>
                <Item.Description>
                    Otterbot is a chatops bot. It is a scalable Slack bot with an extensible framework.
                </Item.Description>
                <Item.Extra>
                    <Label size="tiny" color="blue">
                        <Icon name="tag" />
                        AWS
                    </Label>
                    <Label size="tiny" color="blue">
                        <Icon name="tag" />
                        Account
                    </Label>
                    <Label size="tiny" color="blue">
                        <Icon name="tag" />
                        Metadata
                    </Label>
                </Item.Extra>
            </Item.Content>
        </Item>
        <Item>
            <Item.Image size='tiny' src='/static/logos/infrasec/MikeCloudNoGradientWithFace.png' />
            <Item.Content>
                <Item.Header as='a'>Lazy Falcon</Item.Header>
                <Item.Meta>Description</Item.Meta>
                <Item.Description>
                    Lazy Falcon allows adding / removing IPs from WhiteCastle.
                </Item.Description>
                <Item.Extra>
                    <Label size="tiny" color="blue">
                        <Icon name="tag" />
                        AWS
                    </Label>
                    <Label size="tiny" color="blue">
                        <Icon name="tag" />
                        Account
                    </Label>
                    <Label size="tiny" color="blue">
                        <Icon name="tag" />
                        Metadata
                    </Label>
                </Item.Extra>
            </Item.Content>
        </Item>
        <Item>
            <Item.Image size='tiny' src='/static/logos/infrasec/MikeCloudNoGradientWithFace.png' />
            <Item.Content>
                <Item.Header as='a'>Security Monkey</Item.Header>
                <Item.Meta>Description</Item.Meta>
                <Item.Description>
                    SecurityMonkey enumerates and retrieves metadata from resources in our AWS environments and retains a snapshot history of those resources, allowing them to be searched, inspected and diffed through a single web interface.
                </Item.Description>
                <Item.Extra>
                    <Label size="tiny" color="blue">
                        <Icon name="tag" />
                        AWS
                    </Label>
                    <Label size="tiny" color="blue">
                        <Icon name="tag" />
                        Account
                    </Label>
                    <Label size="tiny" color="blue">
                        <Icon name="tag" />
                        Metadata
                    </Label>
                </Item.Extra>
            </Item.Content>
        </Item>
    </Item.Group>
);

class Landing extends Component {
    state = initialState;

    handleItemClick = (e, { name }) => this.setState({ activeItem: name });

    handleResultSelect = (e, { result }) => this.setState({ value: result.title });

    handleSearchChange = (e, { value }) => {
        this.setState({ isLoading: true, value })

        setTimeout(() => {
            if (this.state.value.length < 1) return this.setState(initialState);

            const re = new RegExp(_.escapeRegExp(this.state.value), 'i');
            const isMatch = (result) => re.test(result.title);

            const filteredResults = _.reduce(
                source,
                (memo, data, name) => {
                    const results = _.filter(data.results, isMatch);
                    if (results.length) memo[name] = { name, results }; // eslint-disable-line no-param-reassign

                    return memo
                },
                {},
            );

            this.setState({
                isLoading: false,
                results: filteredResults,
            })
        }, 300)
    };

    render() {
        const { activeItem, isLoading, value, results } = this.state;

        return (
            <Segment.Group>
                <Segment clearing basic>
                    <Header as="h2" floated="left" textAlign="left">
                        Service Catalog
                        <Header.Subheader>
                            Please search and select self services
                        </Header.Subheader>
                    </Header>
                    <Header floated="right">
                        <Search
                            fluid
                            category
                            loading={isLoading}
                            onResultSelect={this.handleResultSelect}
                            onSearchChange={_.debounce(this.handleSearchChange, 500, {
                                leading: true,
                            })}
                            results={results}
                            value={value}
                        />
                    </Header>
                </Segment>
                <Segment basic>
                    <Menu pointing secondary>
                        <Menu.Item
                            name='all'
                            active={activeItem === 'all'}
                            onClick={this.handleItemClick}
                        />
                        <Menu.Item
                            name='account'
                            active={activeItem === 'account'}
                            onClick={this.handleItemClick}
                        />
                        <Menu.Item
                            name='IAM'
                            active={activeItem === 'IAM'}
                            onClick={this.handleItemClick}
                        />
                        <Menu.Item
                            name='misc'
                            active={activeItem === 'misc'}
                            onClick={this.handleItemClick}
                        />
                    </Menu>
                    <CatalogItems />
                </Segment>
            </Segment.Group>
        );
    }
}

export default Landing;