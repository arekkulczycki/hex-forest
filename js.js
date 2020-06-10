let socket;
const script = document.getElementsByTagName('script')[2];
const mode = script.getAttribute('mode');
const blackColor = script.getAttribute('black-color');
const whiteColor = script.getAttribute('white-color');
const storeMinimum = script.getAttribute('store-minimum');

function connect() {
    let wsAddress = script.getAttribute('ws-address');
    socket = new WebSocket(wsAddress);

    socket.onopen = function (e) {
        console.log('Connection established');
        console.log('Sending to server');
        socket.send('socket opened');

        let name = Cookies.get('hex_forest_name');
        setName(name);
    };

    socket.onmessage = function (event) {
        let data = JSON.parse(event.data);
        console.log(data);
        let playerId;
        let playerName;
        switch (data.type) {
            case 'info':
                console.log(data.message);
                break;
            case 'alert':
                alert(data.message);
                break;
            case 'players':
                for (let i=0; i<data.players.length; i++) {
                    playerId = data.players[i].id;
                    playerName = data.players[i].name;
                    if (playerName === '__name__')
                        playerName = Cookies.get('hex_forest_name');
                    if (playerId === 1 || playerId === 2)
                        assignPlayer(playerId, playerName);
                    else {
                        if ($(`#${playerId}`).length === 0) {
                            let spectators = $('.spectators');
                            let spectator = `<div id="${playerId}" class="spectator-name">${playerName}</div>`;
                            spectators.append(spectator);
                        }
                    }
                }
                break;
            case 'playerIn':
                playerId = data.player_id;
                playerName = data.player_name;
                if (playerId === 1 || playerId === 2)
                    assignPlayer(playerId, playerName);
                else {
                    if ($(`#${playerId}`).length === 0) {
                        let spectators = $('.spectators');
                        let spectator = `<div id="${playerId}" class="spectator-name">${playerName}</div>`;
                        spectators.append(spectator);
                    }
                }
                break;
            case 'playerOut':
                removePlayer(data.player_id);
                break;
            case 'playerName':
                playerId = data.player_id;
                playerName = data.player_name;
                console.log(playerId, playerName);
                if (data.player_id === 1)
                    $('#player_1_box_text').html(playerName);
                else if (data.player_id === 2)
                    $('#player_2_box_text').html(playerName);
                else
                    $(`#${playerId}`).html(playerName);
                break;
            case 'takeSpot':
                let oldId = data.player_old_id;
                playerId = data.player_id;
                playerName = data.player_name;
                if (oldId === 1) {
                    $('#player_1_box_text').html('click to play');
                } else if (oldId === 2) {
                    $('#player_2_box_text').html('click to play');
                } else {
                    removePlayer(oldId);
                }
                assignPlayer(playerId, playerName);
                break;
            case 'leaveSpot':
                if (data.spot === 1)
                    $('#player_1_box_text').html('click to play');
                else if (data.spot === 2)
                    $('#player_2_box_text').html('click to play');
                break;
            case 'move':
                let player_id = data.move.player_id;
                let id = data.move.id;
                let cx = data.move.cx;
                let cy = data.move.cy;
                putStone(id, cx, cy, player_id);
                break;
            case 'remove':
                console.log(data.message);
                removeStone(data.id);
                break;
            case 'clear':
                console.log(data.message);
                clearBoard();
                break;
            case 'chat':
                handleMessage(data.player_id, data.message);
                break;
            case 'saved':
                $('#game_id').val(data.game_id);
                break;
            case 'hint':
                showHint(data.move, data.winner.toString());
                break;
            case 'result':
                showWinner(parseInt(data.winner));
                break;
            case 'kicked':
                alert(data.message);
                break;
            default:
                console.log('Unsupported event', data)
        }
    };

    socket.onclose = function (event) {
        if (event.wasClean) {
            console.log(`Connection closed cleanly, code=${event.code}
                reason=${event.reason}`);
        } else {
            console.log('Connection died');
            console.log('Trying to reconnect...');
            setTimeout(function() {
                connect();
            }, 1000);
        }
    };

    socket.onerror = function (error) {
        console.log(`[error] ${error.message}`);
    };
}
connect();

function handleMessage(player_id, message) {
    let message_block = `<div class="message message_${player_id}">${message}</div>`;
    let chat = $('#chat');
    chat.append(message_block);
    chat.animate({scrollTop: chat.height()}, 500);
}

function toggleResult() {
    let result = $('#position-result');
    if ($('#hints').prop('checked'))
        result.show();
    else
        result.hide();
}

function joinBoard(spot) {
    if (mode === 'free'){
        alert('Not needed in free mode!');
        return;
    }

    let message = {
        'action': 'join_board',
        'spot': spot
    };
    socket.send(JSON.stringify(message))
}

function showWinner(winner) {
    toggleResult();
    let winner_name = winner === 0 ? 'not solved' : (winner === 1 ? 'black' : 'white');
    $('#winner').html(winner_name);
}

function showHint(move, winner) {
    let cell_id = coordsToId(move);
    let cell = $(`#${cell_id}`);

    if (winner === '0')
        cell.css('fill', 'url(#Mixed)');
    else if (winner === blackColor)
        cell.css('fill', 'url(#Black)');
    else if (winner === whiteColor)
        cell.css('fill', 'url(#White)');
}

function clearHints() {
    $('#board').find('.cell').each((i, e) => {
        $(e).css('fill', '#FFCF79');
    });
}

function assignPlayer(player_id, player_name) {
    $(`#player_${player_id}_box_text`).text(player_name)
}

function removePlayer(player_id, player_name) {
    if (player_id === 1 || player_id === 2)
        $(`#player_${player_id}_box_text`).html('click to play');
    else
        $(`#${player_id}`).remove();
}

function boardClick(row, column) {
    let message = {
        'action': 'board_click',
        'row': row,
        'column': column,
        'alternate': $('#alternate').prop('checked'),
        'hints': $('#hints').prop('checked')
    };
    socket.send(JSON.stringify(message))
}

function sendStore(winningPlayerId) {
    $('#storeWhite').prop('disabled', 'disabled');
    $('#storeBlack').prop('disabled', 'disabled');
    setTimeout(() => {
        $('#storeWhite').prop('disabled', false);
        $('#storeBlack').prop('disabled', false);
    }, 3000);

    let message = {
        'action': 'store',
        'opening': $('#opening-decoded').val(),
        'position': getAllStones(),
        'result': winningPlayerId,
    };
    socket.send(JSON.stringify(message));
}

function getAllStones() {
    let stones = [];
    $('#board').find('circle').each((i, e) => {
        let color = $(e).attr('fill') === 'white' ? whiteColor : blackColor;
        stones.push(`${e.id}-${color}`);
    });
    return stones;
}

function saveGame() {
    let message = {
        'action': 'save',
        'game_id': $('#game_id').val()
    };
    socket.send(JSON.stringify(message))
}

function loadGame(game_id = null) {
    if (game_id === null)
        game_id = $('#game_id').val();
    let message = {
        'action': 'load',
        'game_id': game_id
    };
    console.log(message);
    socket.send(JSON.stringify(message))
}

function sendUndo() {
    let message = {
        'action': 'undo'
    };
    socket.send(JSON.stringify(message))
}

function sendSwap() {
    let message = {
        'action': 'swap'
    };
    socket.send(JSON.stringify(message))
}

function sendClearBoard() {
    let message = {
        'action': 'clear'
    };
    socket.send(JSON.stringify(message));
}

function clearBoard() {
    clearHints();
    $('#board').find(`circle`).each((i, e) => {
        e.remove();
    });
}

function sendRemoveStone(id) {
    let message = {
        'action': 'remove',
        'id': id
    };
    socket.send(JSON.stringify(message))
}

let map = {}; // You could also use an array
onkeydown = onkeyup = function(e){
    e = e || event; // to deal with IE
    map[e.keyCode] = e.type === 'keydown';
    /* insert conditional here */
};

function trySendMessage(e) {
    let key = window.event.keyCode;
    if ((16 in map && !map[16] && key === 13) ||
        (!(16 in map) && key === 13)) {
        window.event.preventDefault();
        sendMessage()
    }
}

function sendMessage() {
    let messageBox = $('#message');
    let message = {
        'action': 'chat',
        'message': messageBox.val()
    };
    socket.send(JSON.stringify(message));

    messageBox.val('');
}

function removeStone(id) {
    $(`#${id}`).remove();

    setOpening();

    clearHints();

    if ($('#hints').prop('checked'))
        sendLoadHints();
}

function putStone(id, cx, cy, player_id) {
    let fill = player_id === 1 ? 'black' : 'white';

    let xmlns = 'http://www.w3.org/2000/svg';
    let stone = document.createElementNS(xmlns,'circle');
    stone.setAttributeNS(null, 'id', id);
    stone.setAttributeNS(null, 'cx', cx);
    stone.setAttributeNS(null, 'cy', cy);
    stone.setAttributeNS(null, 'r', '11.0');
    stone.setAttributeNS(null, 'fill', fill);
    stone.setAttributeNS(null, 'onclick', `sendRemoveStone('${id}')`);

    $('#board').append(stone);

    clearHints();

    setOpening();
    if (mode === 'free' && $('#hints').prop('checked'))
        sendLoadHints();
}

function sendLoadHints() {
    let message = {
        'action': 'hints',
        'opening': $('#opening-decoded').val(),
        'position': getAllStones()
    };
    socket.send(JSON.stringify(message))
}

function setOpening() {
    let stones = getAllStones();
    //if (stones.length === 2) {
    //    $('#swap').prop('disabled', 'disabled');
    //
    //    $('#storeWhite').prop('disabled', 'disabled');
    //    $('#storeBlack').prop('disabled', 'disabled');
    //
    //    let first = coordsToId(stones[0]);
    //    let second = coordsToId(stones[1]);
    //    $('#opening-decoded').val(`${first},${second}`);
    //}
    if (stones.length === 1) {
        $('#swap').prop('disabled', false);

        $('#storeWhite').prop('disabled', 'disabled');
        $('#storeBlack').prop('disabled', 'disabled');

        let first = coordsToId(stones[0]);
        $('#opening-decoded').val(first);
    }
    else if (stones.length < storeMinimum) {
        $('#swap').prop('disabled', 'disabled');

        $('#storeWhite').prop('disabled', 'disabled');
        $('#storeBlack').prop('disabled', 'disabled');
    }
    else {
        $('#swap').prop('disabled', 'disabled');

        $('#storeWhite').prop('disabled', false);
        $('#storeBlack').prop('disabled', false);
    }
}

function coordsToId(coords) {
    let split = coords.split('-');
    if (split.length < 2)
        return null;
    let first = String.fromCharCode(65 + parseInt(split[1])).toLowerCase();
    return `${first}${parseInt(split[0]) + 1}`
}

function changeName() {
    let name = $('#nickname').val();
    Cookies.set('hex_forest_name', name);

    setName(name);
}

function setName(name) {
    $('#nickname').val(name);

    let message = {
        'action': 'name',
        'name': name
    };
    socket.send(JSON.stringify(message))
}

function kickPlayer(player_id) {
    let message = {
        'action': 'kick',
        'player_id': player_id
    };
    socket.send(JSON.stringify(message))
}