
export async function authenticateUser(username, password) {
    let res = await fetch('/auth', {
                method: 'POST',
                body: JSON.stringify({'username': username, 'password': password})
                })
    let data = await res.json();
    return data
}

export async function getDashboard(username, token) {
    let data = {};
    let res = await fetch('/get_dashboard', {
                method: 'POST',
                body: JSON.stringify({'username': username, 'token': token}),
                })
    try {
        data = await res.json();
    } catch (error){
        console.error(error)
    }
    return data
}

export async function getAllQueries(username, token) {
    let data = {};
    let res = await fetch('/get_all_queries', {
                method: 'POST',
                body: JSON.stringify({'username': username, 'token': token}),
                })
    try {
        data = await res.json();
    } catch (error){
        console.error(error)
    }
    return data
}

export async function addQuery(username, token, query_data) {
    let data = {};
    query_data['username'] = username
    query_data['token'] = token
    let res = await fetch('/add_query', {
                method: 'POST',
                body: JSON.stringify(query_data),
                })
    try {
        data = await res.json();
    } catch (error){
        console.error(error)
    }
    return data
}

export async function editQuery(username, token, query_data) {
    let data = {};
    query_data['username'] = username
    query_data['token'] = token
    let res = await fetch('/edit_query', {
                method: 'POST',
                body: JSON.stringify(query_data),
                })
    try {
        data = await res.json();
    } catch (error){
        console.error(error)
    }
    return data
}

export async function saveQuery(username, token) {
    let data = {};
    let res = await fetch('/save', {
                method: 'POST',
                body: JSON.stringify({'username': username, 'token': token}),
                })
    try {
        data = await res.json();
    } catch (error){
        console.error(error)
    }
    return data
}

export async function getSound(username, token, alert_sound) {
    let source;
    let res = await fetch('/get_sound', {
                method: 'POST',
                body: JSON.stringify({'username': username, 'token': token, 'alert_sound': alert_sound}),
                })
    try {
        let sound = await res.body.getReader().read();
        let context = new AudioContext()
        let a_buffer = await context.decodeAudioData(sound.value.buffer)
        source = context.createBufferSource()
        source.buffer = a_buffer
        source.connect(context.destination)
    } catch (error){
        console.error(error)
    }
    return source
}

export async function deleteQuery(username, token, uid) {
    let data = {};
    let res = await fetch('/delete_query', {
                method: 'POST',
                body: JSON.stringify({'username': username, 'token': token, 'uid': uid}),
                })
    try {
        data = await res.json();
    } catch (error){
        console.error(error)
    }
    return data
}

export async function getSettings(username, token) {
    let data = {};
    let res = await fetch('/get_settings', {
                method: 'POST',
                body: JSON.stringify({'username': username, 'token': token}),
            })
    try {
        data = await res.json();
    } catch (error){
        console.error(error)
    }
    return data
}

export async function editSettings(username, token, new_data) {
    let data = {};
    new_data['username'] = username
    new_data['token'] = token
    let res = await fetch('/edit_settings', {
                method: 'POST',
                body: JSON.stringify(new_data),
            })
    try {
        data = await res.json();
    } catch (error){
        console.error(error)
    }
    return data
}