<?php

$config = array(

    'admin' => array(
        'core:AdminPassword',
    ),

    'example-userpass' => array(
        'exampleauth:UserPass',
        'consoleme_user:consoleme_user' => array(
            'uid' => array('1'),
            'groups' => array('groupa@example.com', 'groupb@example.com'),
            'email' => 'consoleme_user@example.com',
        ),
        'consoleme_admin:consoleme_admin' => array(
            'uid' => array('2'),
            'groups' => array('groupa@example.com', 'group2@example.com', 'consoleme_admin@example.com'),
            'email' => 'consoleme_admin@example.com',
        ),
    ),

);