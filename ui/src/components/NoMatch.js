import { Header, Image, Segment } from "semantic-ui-react";

const NoMatch = () => (
  <Segment
    basic
    style={{
      paddingTop: "120px",
      marginTop: "72px",
      marginLeft: "240px",
    }}
    textAlign="center"
  >
    <Header
      as="h1"
      color="grey"
      style={{
        fontSize: "74px",
      }}
      textAlign="center"
    >
      404
      <Header.Subheader>We were unable to console you!</Header.Subheader>
    </Header>
    <Image
      centered
      disabled
      size="medium"
      src="/images/logos/quarantine/1.png"
    />
  </Segment>
);

export default NoMatch;
