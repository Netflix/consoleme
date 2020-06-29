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

export async function getCookie(name) {
  let r = document.cookie.match('\\b' + name + '=([^;]*)\\b')
  return r ? r[1] : undefined
}

export async function sendRequestCommon(json, location = window.location.href) {
    const xsrf = await getCookie('_xsrf');
    const rawResponse = await fetch(location, {
        method: 'post',
        headers: {
            'Content-type': 'application/json',
            'X-Xsrftoken': xsrf,
        },
        body: JSON.stringify(json),
    });

    const response = await rawResponse;

    let resJson;
    try {
        resJson = response.json();
    } catch (e) {
        resJson = response;
    }

    return await resJson;
}