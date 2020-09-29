import _ from 'lodash';
import React, {useState, useEffect, useContext} from 'react';
import {
    Icon,
    Item,
    Label,
    Header,
    Menu,
    Search,
    Segment,
} from 'semantic-ui-react';

const initialState = {
    activeItem: 'all',
    isLoading: false,
    results: [],
    value: ''
};

const CatalogItems = () => (
    <Item.Group divided relaxed>
        <Item>
            <Item.Image as="a" href="/selfservice" size='tiny' src='/images/logos/nosunglasses/1.png' />
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
            <Item.Image as='a' hfre="https://go/honeybee" size='tiny' src='/images/logos/infrasec/Honeybee.png' />
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
            <Item.Image size='tiny' src='/images/logos/sunglasses/1.png' />
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
            <Item.Image size='tiny' src='/images/logos/sunglasses/3.png' />
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
            <Item.Image size='tiny' src='/images/logos/infrasec/MikeCloudNoGradientWithFace.png' />
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
            <Item.Image size='tiny' src='/images/logos/infrasec/MikeCloudNoGradientWithFace.png' />
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
            <Item.Image size='tiny' src='/images/logos/infrasec/MikeCloudNoGradientWithFace.png' />
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
            <Item.Image size='tiny' src='/images/logos/infrasec/MikeCloudNoGradientWithFace.png' />
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

function Catalog() {
    const [activeItem, setActiveItem] = useState('all');
    const [isLoading, setLoading] = useState(false);
    const [value, setValue] = useState('');
    const [results, setResults] = useState([]);

    const handleActiveItem = (e, { name }) => setActiveItem(name);
    const handleResultSelect = (e, { result }) => setResults(result.title);
    const handleSearchChange = (e, { value }) => {
        setLoading(false);
        setResults(value);
    };

    useEffect(() => {
        console.log('effected');
        return () => {
            console.log("unmounted");
        };
    }, [activeItem]);

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
                        onResultSelect={handleResultSelect}
                        onSearchChange={_.debounce(handleSearchChange, 500, {
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
                        onClick={handleActiveItem}
                    />
                    <Menu.Item
                        name='account'
                        active={activeItem === 'account'}
                        onClick={handleActiveItem}
                    />
                    <Menu.Item
                        name='IAM'
                        active={activeItem === 'IAM'}
                        onClick={handleActiveItem}
                    />
                    <Menu.Item
                        name='misc'
                        active={activeItem === 'misc'}
                        onClick={handleActiveItem}
                    />
                </Menu>
                <CatalogItems />
            </Segment>
        </Segment.Group>
    );
}

export default Catalog;