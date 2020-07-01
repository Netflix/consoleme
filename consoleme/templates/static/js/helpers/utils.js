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


export function PolicyTypeahead(resource_type, value, account_id = null, callback, limit = 20) {
        let url = "/policies/typeahead?resource=" + resource_type + "&search=" + value + "&limit=" + limit
        if (account_id) {
          url += "&account_id=" + account_id
        }

        const resp = fetch(url).then((resp) => {
            resp.text().then((resp) => {
                const result = JSON.parse(resp);
                let matching_resources = []
                results.forEach(function (result) {
                    // Strip out what the user has currently typed (`row`) from the full value returned from typeahead
                    const v = result.title.replace(row, row[row.length - 1]);
                    matching_resources.push({name: result.title, value: v, meta: "Resource", score: 1000})
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
    let regions = [
        {"region": "us-east-1", "type": "region"},
        {"region": "us-west-2", "type": "region"},
        {"region": "eu-west-1", "type": "region"},
    ]
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
        // We know we're in the Resource section, so let's help type the ARN starting with the prefix
        // of `arn:aws:<resource_type>`
        if ("arn:aws:".indexOf(row) > -1 && row.length < 9) {
            callback(null, resources.map(function (ea) {
                return {name: ea.resource, value: ea.resource, meta: "Resource", score: 1000}
            }));
        } else if (row.indexOf("arn:aws:") > -1) {
            // We have `arn:aws:<resource_type>`, now let's help type of the region if necessary
            const splitted = row.split(":")
            if (splitted.length === 4 && splitted[2] !== "s3") {
                callback(null, regions.map(function (ea) {
                    return {name: ea.region, value: ea.region, meta: "Region", score: 1000}
                }));
                return
            }
            let resource_type = null
            resources.forEach(function (r) {
                if (row.indexOf(r.resource) > -1) {
                    resource_type = r.type
                }
            });
            if (resource_type !== null) {
                row = row.replace("arn:aws:s3:::", "")
                let results = new PolicyTypeahead(resource_type, row, null, callback, 100)
            }
        }
    }
}