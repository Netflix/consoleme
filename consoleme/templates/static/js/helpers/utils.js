import SelfServiceComponent from "../components/SelfServiceComponent";

const ALPHABET = '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ';

export function random_id() {
    let rtn = '';
    for (let i = 0; i < 8; i++) {
        rtn += ALPHABET.charAt(Math.floor(Math.random() * ALPHABET.length));
    }
    return rtn;
}

export function generate_id() {
    return "ConsoleMe" + random_id();
}

export function generate_temp_id(expiration_date) {
    return "temp_" + expiration_date + "_" + random_id();
}

export function generateBasePolicy() {
    return {
        "Action": [],
        "Effect": "Allow",
        "Resource": [],
        "Sid": generate_id(),
    };
}

export function getServiceTypes() {
    // List of available self service items.
    return Object.keys(SelfServiceComponent.components).map(service => {
        const component = SelfServiceComponent.components[service];
        return {
            actions: component.ACTIONS,
            key: component.TYPE,
            value: component.TYPE,
            text: component.NAME,
        };
    });
}

export async function getCookie(name) {
  let r = document.cookie.match('\\b' + name + '=([^;]*)\\b')
  return r ? r[1] : undefined
}

export async function sendRequestCommon(json, location = window.location.href) {
    let xsrf = await getCookie('_xsrf');
    const rawResponse = await fetch(location, {
        method: 'post',
        headers: {
            'Content-type': 'application/json',
            'X-Xsrftoken': xsrf,
        },
        body: json
    });

    let res = await rawResponse;

    let resJson;
    try {
        resJson = res.json();
    } catch (e) {
        resJson = res;
    }
    return await resJson;
}