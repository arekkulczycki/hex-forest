const WebSocketClient = require('simple-websocket');
let socket;

const script = document.getElementsByTagName('script')[3];
const mode = script.getAttribute('mode');
const blackColor = false;
const whiteColor = true;
const storeMinimum = 10;
var timeout = null;
var lastMoveColor = true;
var moveStack = [];

function whenAvailable(name, callback) {
    var interval = 10; // ms
    window.setTimeout(function() {
        if (window[name]) {
            callback(window[name]);
        } else {
            whenAvailable(name, callback);
        }
    }, interval);
}

function identifyPlayer() {
    let pin = Cookies.get('livehex-pin');
    let message = {
        'action': 'assign_player',
        'pin': pin ?? null
    };
    socket.send(JSON.stringify(message))

    console.log('Player identified');
}

function setupEvents() {
    let is_analysis = window.location.pathname.indexOf('/analysis') !== -1;

    if (is_analysis) {
        document.addEventListener('keyup', (event) => {
            if (event.code === 'ArrowLeft') {
                arrowLeft();
            }
        }, false);
        fillMoveStack();
    }
}

function cleanUrl() {
    window.history.pushState({}, document.title, window.location.pathname);
}

function connect() {
    setupEvents();
    cleanUrl();

    let wsAddress = script.getAttribute('ws-address');
    let prefix = location.protocol === 'https:' ? 'wss' : 'ws';
    // socket = new WebSocket(`${prefix}${wsAddress}`);
    socket = new WebSocketClient({
        url: `${prefix}${wsAddress}`,
        protocolVersion: 13,
        // origin: origin,
        rejectUnauthorized: false
    });

    // socket.onopen = function (e) {
    socket.on('connect', function () {
        console.log('Connection established');

        whenAvailable('Cookies', identifyPlayer);
    });

    // socket.onmessage = function (event) {
    socket.on('data', function (data) {
        // let data = JSON.parse(event.data);
        console.log(data);
        let playerId;
        let playerName;
        switch (data.action) {
            case 'info':
                console.log(data.message);
                break;
            case 'alert':
                alert(data.message);
                break;
            case 'joined':
                handlePlayerJoined(data);
                break;
            case 'leaved':
                handlePlayerLeaved(data);
                break;
            case 'move':
                handleMove(data);
                break;
            case 'remove':
                removeStone(data.id);
                break;
            case 'clear':
                clearBoard();
                break;
            case 'takeSpot':
                takeSpot(data)
                break;
            case 'takeSpotAi':
                takeSpotAi(data)
                break;
            case 'leaveSpot':
                leaveSpot(data)
                break;
            case 'gameStarted':
                gameStarted(data)
                break;
            case 'showSwap':
                showSwap(data)
                break;
            case 'swapped':
                swapped(data);
                break;
            case 'passed':
                passed(data);
                break;
            case 'chat_message':
                chatMessage(data);
                break;
            case 'resigned':
                handleResigned(data);
                break;

            case 'undo':
                undo(data);
                break;
            case 'players':
                for (let i=0; i<data.players.length; i++) {
                    playerId = data.players[i].id;
                    playerName = data.players[i].name;
                    if (playerName === '__name__') {
                        playerName = Cookies.get('hex_forest_name');
                    }
                    if (playerId === 1 || playerId === 2) {
                        assignPlayer(playerId, playerName);
                    } else {
                        if ($(`#${playerId}`).length === 0) {
                            let spectators = $('.spectators');
                            let spectator = `<div id="${playerId}" class="spectator-name">${playerName}</div>`;
                            spectators.append(spectator);
                        }
                    }
                }
                break;
            case 'playerIn':
                playerId = 0;  // TODO: change handling of player assignment
                playerName = data.player_name;
                if (playerId === 1 || playerId === 2) {
                    assignPlayer(playerId, playerName);
                } else {
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
                if (data.player_id === 1) {
                    $('#black_box_text').html(playerName);
                } else if (data.player_id === 2) {
                    $('#white_box_text').html(playerName);
                } else {
                    $(`#${playerId}`).html(playerName);
                }
                break;
            case 'mark':
                let markId = data.move.id;
                let MarkCx = data.move.cx;
                let MarkCy = data.move.cy;
                putMarker(markId, MarkCx, MarkCy);
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
    });

    // socket.onclose = function (event) {
    socket.on('close', function () {
        // if (event.wasClean) {
        //     console.log(`Connection closed cleanly, code=${event.code}
        //         reason=${event.reason}`);
        // } else {
        console.log('Connection died, trying to reconnect...');
        setTimeout(function() {
            connect();
        }, 1000);
        // }
    });

    // socket.onerror = function (error) {
    socket.on('error', function (error) {
        console.log(`[error] ${error.message}`);
    });
}
window.onload = connect;
// connect();

function chatMessage(data) {
    let playerName = data.player_name;
    let white = $('#white_box_text');
    let black = $('#black_box_text');

    let color = white.html().trim() === playerName ? 'white' : (black.html().trim() === playerName ? 'black' : 'blue');

    let message_block = `<div class="message message_${color}">${playerName}>&nbsp;${data.message}</div>`;
    let chat = $('#chat');
    chat.prepend(message_block);
    // chat.animate({scrollTop: chat.prop('scrollHeight')}, 750);
}

function toggleResult() {
    let result = $('#position-result');
    if ($('#hints').prop('checked')) {
        result.show();
    } else {
        result.hide();
    }
}

function joinBoard(color) {
    if (mode === 'free'){
        alert('Not needed in free mode!');
        return;
    }

    let message = {
        'action': 'board_join',
        'color': color,
        'game_id': window.location.href.split('/').at(-1)
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

    if (winner === '0') {
        cell.css('fill', 'url(#Mixed)');
    } else if (winner === blackColor) {
        cell.css('fill', 'url(#Black)');
    } else if (winner === whiteColor) {
        cell.css('fill', 'url(#White)');
    }
}

function clearHints() {
    $('#board').find('.cell').each((i, e) => {
        $(e).css('fill', '');
    });
}

function assignPlayer(player_id, player_name) {
    $(`#player_${player_id}_box_text`).text(player_name)
}

function removePlayer(player_id, player_name) {
    if (player_id === 1 || player_id === 2) {
        $(`#player_${player_id}_box_text`).html('join');
    } else {
        $(`#${player_id}`).remove();
    }
}

function boardClick(cell_id) {
    let colorMode = $('#color_alternate').prop('checked') ? 'alternate' :
        ($('#color_black').prop('checked') ? 'black' : 'white');

    let color
    if (colorMode === 'alternate') {
        let moves = getAllMoves();
        let nWhiteMoves = moves.filter(x => x.color).length;
        let nBlackMoves = moves.length - nWhiteMoves;
        color = nWhiteMoves < nBlackMoves;
    } else {
        color = colorMode === 'white'
    }

    let is_analysis = window.location.pathname.indexOf('/analysis') !== -1;
    let existingStoneId = getStoneIdIfExists(cell_id);
    if (is_analysis && existingStoneId) {
        removeStone(existingStoneId);
    } else if (is_analysis) {
        // TODO: maybe putStone, but for now ignore, maybe remove the boardClick function altogether
    } else {
        let message = {
            'action': 'board_put',
            'mode': is_analysis ? 'analysis' : 'game',
            'game_id': is_analysis ? null : window.location.href.split('/').at(-1),
            'cell_id': cell_id,
            'color': color,
        };
        socket.send(JSON.stringify(message))
    }
}

function getStoneIdIfExists(cell_id) {
    if ($(`#${cell_id}-w`).length) {
        return `${cell_id}-w`;
    } else if ($(`#${cell_id}-b`).length) {
        return `${cell_id}-b`;
    } else {
        return null;
    }
}

function boardHover(id) {
    $('#coords').html(id);

    $(`#${id}`).addClass('hover');

    if (timeout != null) {
        clearTimeout(timeout);
    }

    timeout = setTimeout(() => {
        $('#coords').html('');
    }, 1000);
}

function boardUnhover(id) {
    $(`#${id}`).removeClass('hover');
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
        'position': getAllStoneIds(),
        'result': winningPlayerId,
    };
    socket.send(JSON.stringify(message));
}

function getAllStoneIds() {
    let stones = [];
    $('#board').find('circle').each((i, e) => {
        if (e.id !== 'lastMoveMarker') {
            stones.push(e.id);
        }
    });
    return stones;
}

function getAllStones() {
    let stones = [];
    $('#board').find('circle').each((i, e) => {
        if (e.id !== 'lastMoveMarker') {
            stones.push($(`#${e.id}`));
        }
    });
    return stones;
}

function fillMoveStack() {
    let stones = getAllStones();
    stones = stones.sort((s1, s2) => {return s1[0].order - s2[0].order});
    stones.forEach((stone, i) => {
        moveStack.push(stone[0].id);
    });
}

function saveGame() {
    let message = {
        'action': 'save',
        'game_id': $('#game_id').val()
    };
    socket.send(JSON.stringify(message))
}

function loadGame(game_id = null) {
    if (game_id === null) {
        game_id = $('#game_id').val();
    }
    let message = {
        'action': 'load',
        'game_id': game_id
    };
    console.log(message);
    socket.send(JSON.stringify(message))
}

function lgImport(game_id = null) {
    if (game_id === null) {
        game_id = $('#game_id').val();
    }
    let message = {
        'action': 'import',
        'game_id': game_id
    };
    console.log(message);
    socket.send(JSON.stringify(message))
}

function sendUndo() {
    let message = {
        'action': 'board_undo',
        'game_id': window.location.href.split('/').at(-1)
    };
    socket.send(JSON.stringify(message))
}

function sendResign() {
    let message = {
        'action': 'board_resign',
        'game_id': window.location.href.split('/').at(-1)
    };
    socket.send(JSON.stringify(message))
}

function sendSwap() {
    let message = {
        'action': 'board_swap',
        'game_id': window.location.href.split('/').at(-1)
    };
    socket.send(JSON.stringify(message))
}

function sendPass() {
    let message = {
        'action': 'board_pass',
        'game_id': window.location.href.split('/').at(-1)
    };
    socket.send(JSON.stringify(message))
}

function startGame() {
    let message = {
        'action': 'board_start',
        'game_id': window.location.href.split('/').at(-1)
    };
    socket.send(JSON.stringify(message))
}

function sendClearBoard() {
    let is_analysis = window.location.pathname.indexOf('/analysis') !== -1;

    let message = {
        'action': 'board_clear',
        'mode': is_analysis ? 'analysis' : 'game'
    };
    socket.send(JSON.stringify(message));
}

function clearBoard() {
    $('#board').find(`circle`).each((i, e) => {
        e.remove();
    });
}

function sendRemoveStone(id) {
    let is_analysis = window.location.pathname.indexOf('/analysis') !== -1;

    let message = {
        'action': 'board_remove',
        'id': id,
        'mode': is_analysis ? 'analysis' : 'game'
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
    let text = messageBox.val();
    if (text) {
        let message = {
            'action': 'chat_message',
            'message': messageBox.val()
        };
        socket.send(JSON.stringify(message));
    }

    messageBox.val('');
}

function removeStone(id) {
    if (id.indexOf('ghost') === -1) {
        lastMoveColor = !lastMoveColor;
    }

    let lastMoveMarker = $('#lastMoveMarker');
    if (lastMoveMarker.length) {
        lastMoveMarker.remove();
    }
    $(`#${id}`).remove();

    setOpening();
}

function putStone(cell_id, color, ghost=false) {
    let existingStoneId = getStoneIdIfExists(cell_id);
    let is_analysis = window.location.pathname.indexOf('/analysis') !== -1;
    if (is_analysis && existingStoneId) {
        removeStone(existingStoneId);
        return;
    }

    let cell = $(`#${cell_id}`);
    let lastMoveMarker = $('#lastMoveMarker');
    if (lastMoveMarker.length) {
        lastMoveMarker.remove();
    }

    if (color === null) {
        let a = $('#color_alternate');
        if (a.prop('checked')) {
            color = !lastMoveColor;
        } else {
            let w = $('#color_white');

            color = w.prop('checked');
        }
    }

    let fill = color ? 'white' : 'black';
    let c = color ? 'w' : 'b';

    let xmlns = $('#xmlns').val();
    let stone = document.createElementNS(xmlns,'circle');

    let id = `${cell.attr('id')}-${c}`;
    stone.setAttributeNS(null, 'id', (ghost ? `${id}-ghost` : id));
    stone.setAttributeNS(null, 'cx', cell.attr('cx'));
    stone.setAttributeNS(null, 'cy', cell.attr('cy'));
    stone.setAttributeNS(null, 'r', '11.0');
    stone.setAttributeNS(null, 'fill', fill);

    if (!ghost) {
        if (is_analysis) {
            stone.setAttributeNS(null, 'onclick', `removeStone('${id}');`);
        } else {
            stone.setAttributeNS(null, 'onclick', `sendRemoveStone('${id}');`);
        }
        $('#board').append(stone);
        putMarker(id, cell.attr("cx"), cell.attr("cy"));

        moveStack.push(id);

        if (getAllStoneIds().length === 1) {
            $(`#swap`).css('display', 'block');
        } else {
            $(`#swap`).css('display', 'none');
        }

        lastMoveColor = !lastMoveColor;
    } else {
        stone.setAttributeNS(null, 'onclick', `removeStone('${id}-ghost'); putStone('${cell_id}', null, false);`);
        stone.setAttributeNS(null, 'oncontextmenu', `removeStone('${id}-ghost'); return false;`);
        stone.setAttributeNS(null, 'opacity', `40%`);

        $('#board').append(stone);
    }

    // clearHints();
    //
    // setOpening();
    // if (mode === 'free' && $('#hints').prop('checked')) {
    //     sendLoadHints();
    // }
    return false;
}

function arrowLeft() {
    let id = moveStack.pop();
    removeStone(id);
}

function arrowRight() {

}

function putMarker(id, cx, cy){
    let xmlns = $('#xmlns').val();
    let lastMoveMarker = document.createElementNS(xmlns,'circle');
    lastMoveMarker.setAttributeNS(null, 'id', 'lastMoveMarker');
    lastMoveMarker.setAttributeNS(null, 'cx', cx);
    lastMoveMarker.setAttributeNS(null, 'cy', cy);
    lastMoveMarker.setAttributeNS(null, 'r', '6.0');
    lastMoveMarker.setAttributeNS(null, 'fill', 'red');
    lastMoveMarker.setAttributeNS(null, 'onclick', `sendRemoveStone('${id}')`);
    $('#board').append(lastMoveMarker);
}

function sendLoadHints() {
    let message = {
        'action': 'hints',
        'opening': $('#opening-decoded').val(),
        'position': getAllStoneIds()
    };
    socket.send(JSON.stringify(message))
}

function setOpening() {
    let stones = getAllStoneIds();
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
    } else if (stones.length < storeMinimum) {
        $('#swap').prop('disabled', 'disabled');

        $('#storeWhite').prop('disabled', 'disabled');
        $('#storeBlack').prop('disabled', 'disabled');
    } else {
        $('#swap').prop('disabled', 'disabled');

        $('#storeWhite').prop('disabled', false);
        $('#storeBlack').prop('disabled', false);
    }
}

function coordsToId(coords) {
    let split = coords.split('-');
    if (split.length < 2) {
        return null;
    }
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

function toggleColor(type) {
    let a = $('#color_alternate');
    let b = $('#color_black');
    let w = $('#color_white');
    if (type === 0){
        b.prop('checked', false);
        w.prop('checked', false);
    } else if (type === 1){
        a.prop('checked', false);
        w.prop('checked', false);
    } else {
        a.prop('checked', false);
        b.prop('checked', false);
    }
}

function getNameUrl() {
    let name = $('#name-input').val();
    return `/login/${name}`
}

function getImportUrl() {
    let input = $('#import-input').val();
    if (isNaN(input)) {
        return `/archive/lg_bulk_import/${input}`
    }
    return `/archive/lg_import/${input}`
}

function goToArchive(limit) {
    let moves = getAllMovesUrl();
    if (moves.split(',').length > limit) {
        alert(`At the moment archive permitted for up to ${limit}` + ' moves');
    } else {
        window.location = `/analysis?moves=${getAllMovesUrl()}`;
    }
}

function showWarning() {
    cleanUrl();
    let warning = $('#warning') ?? null;
    if (warning) {
        alert(warning.html());
    }
    warning.remove()
}

function handlePlayerJoined(data) {
    let onlinePlayersList = $('#players-online');
    let playerItem = `<li class="lobby-item">${data.player_name}</li>`;
    onlinePlayersList.append(playerItem);

    if (data.registered) {
        $('#players-offline').find('li').each((i, e) => {
            if ($(e).html().trim() === data.player_name) {
                e.remove();
            }
        });
    }
}

function handlePlayerLeaved(data) {
    $('#players-online').find('li').each((i, e) => {
        if ($(e).html().trim() === data.player_name) {
            console.log(`removing ${data.player_name}`);
            e.remove();
        }
    });

    if (data.registered) {
        let offlinePlayersList = $('#players-offline');
        let playerItem = `<li class="lobby-item">${data.player_name}</li>`;
        offlinePlayersList.append(playerItem);
    }
}

function handleMove(data) {
    let color = data.move.color;
    let id = data.move.id;
    let cell_id = id.split('-')[0];
    putStone(cell_id, color);

    setTurnMarker(!data.move.color);
}

function takeSpot(data) {
    let playerName = data.player_name;
    let color = data.color;

    let white = $('#white_box_text');
    let black = $('#black_box_text');

    if (color) {
        if (black.html().trim() === playerName) {
            black.html("join");
        }
        white.html(playerName);
    } else {
        if (white.html().trim() === playerName) {
            white.html("join");
        }
        black.html(playerName);
    }
}

function takeSpotAi(data) {
    let playerName = data.player_name;
    let color = data.color;

    let white = $('#white_box_text');
    let black = $('#black_box_text');

    if (color) {
        white.html(playerName);
        black.html("AI");
    } else {
        white.html("AI");
        black.html(playerName);
    }
}

function leaveSpot(data) {
    if (data.color) {
        $('#white_box_text').html('join');
    } else {
        $('#black_box_text').html('join');
    }
}

function gameStarted(data) {
    $('#status').html("status: in progress");
    // TODO: dim the background for the nice feel of board focus
    let start = $('#start');
    if (start) {
        start.remove();
    }

    setTurnMarker(false);
}

function showSwap(data) {
    $('#swap').css('visibility', 'visible');
}

function swapped() {
    $('#swap').css('visibility', 'hidden');

    let white = $('#white_box_text');
    let black = $('#black_box_text');

    let blackText = black.html();
    black.html(white.html());
    white.html(blackText);
}

function passed(data) {
    data.moves.forEach((move, i) => {
        let color = move.color;
        let id = move.id;
        let cell_id = id.split('-')[0];
        putStone(cell_id, color);
    });

    setTurnMarker(!data.color);
}

function setTurnMarker(turn) {
    if (turn) {
        $('#white_turn').show();
        $('#black_turn').hide();
    } else {
        $('#black_turn').show();
        $('#white_turn').hide();
    }
}

function getAllMoves() {
    let moves = [];
    $('#board').find('circle').each((i, e) => {
        if (e.id !== 'lastMoveMarker' && e.id.indexOf('ghost') === -1) {
            let color = $(e).attr('fill') === 'white';
            let split = e.id.split('-')
            moves.push({'color': color, 'x': split[0], 'y': split[1]});
        }
    });
    return moves;
}

function getAllMovesUrl() {
    let moves = [];
    $('#board').find('circle').each((i, e) => {
        if (e.id !== 'lastMoveMarker' && e.id.indexOf('ghost') === -1) {
            moves.push(e.id);
        }
    });
    return moves.join(',');
}

function goToRotatedBoard() {
    window.location = `/analysis?moves=${getAllMovesUrl()}&action=rotate`;
}

function goToMirroredBoard() {
    window.location = `/analysis?moves=${getAllMovesUrl()}&action=mirror`;
}

function copyLink() {
    let url = `${window.location.origin}/analysis?moves=${getAllMovesUrl()}`;

    // TODO: when running on ssl
    // navigator.clipboard.writeText(url);

    // Until then, ise the 'out of viewport hidden text area' trick
    const textArea = document.createElement("textarea");
    textArea.value = url;

    // Move textarea out of the viewport so it's not visible
    textArea.style.position = "absolute";
    textArea.style.left = "-999999px";

    document.body.prepend(textArea);
    textArea.select();

    try {
        document.execCommand('copy');
    } catch (error) {
        console.error(error);
    } finally {
        textArea.remove();
    }
}

function handleResigned(data) {
    let color = data['color'] ? ' black ' : ' white ';
    $('#status').html(`status: ${color} won`);

    $('#game-in-progress-options').hide();
}
