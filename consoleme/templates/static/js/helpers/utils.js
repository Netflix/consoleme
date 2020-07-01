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


export function PolicyTypeahead(value, callback, limit = 20) {
        let url = "/api/v2/typeahead/resources?typeahead=" + value + "&limit=" + limit

        fetch(url).then((resp) => {
            resp.text().then((resp) => {
                const results = JSON.parse(resp);
                let matching_resources = []
                results.forEach(function (result) {
                    // Strip out what the user has currently typed (`row`) from the full value returned from typeahead
                    matching_resources.push({name: result, value: result, meta: "Resource", score: 1000})
                })
                callback(null, matching_resources)
            })
        })
      }

export function getCompletions(editor, session, pos, prefix, callback) {
    let resource = false
    let action = false
    const lines = editor.getValue().split("\n")
    for (let i = pos.row; i >= 0; i--) {
        if (lines[i].indexOf('"Resource"') > -1) {
            resource = true
            break
        }

        if (lines[i].indexOf('"Action"') > -1) {
            action = true
            break
        }
    }
    // Check for other statements? The beginning of the statement? The curly bracket?
    // if not action or resource do nothing?
    if (prefix.length === 0 || (action === false && resource === false)) {
        callback(null, []);
        return
    }
    // TODO(ccastrapel): Need generic typeahead for all resource types
    let resources = [
        {"resource": "arn:aws:s3:::", "type": "s3"},
        {"resource": "arn:aws:sqs:", "type": "sqs"},
        {"resource": "arn:aws:sns:", "type": "sns"},
        {"resource": "arn:aws:iam:", "type": "iam_arn"}];
    // TODO(ccastrapel): Regions should be configurable

    let row = session.getDocument().getLine(pos["row"]).trim().replace(/\"/g, "");
    if (action === true) {
        fetch("/api/v1/policyuniverse/autocomplete?prefix=" + row).then((resp) => {
            resp.text().then((resp) => {
                const wordList = JSON.parse(resp);
                // wordList like [{"permission":"s3:GetObject"}]
                callback(null, wordList.map(function (ea) {
                    let value = ea.permission;
                    if (row.indexOf(":") > -1) {
                        value = value.split(":")[1];
                    }
                    return {name: ea.permission, value: value, meta: "Permission", score: 1000}
                }));
            })
        })
    } else if (resource === true) {
        // We know we're in the Resource section, so let's help type the ARN
       new PolicyTypeahead(row, callback, 1000)
    }
}