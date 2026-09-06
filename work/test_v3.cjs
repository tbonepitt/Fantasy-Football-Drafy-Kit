const fs = require('fs');
const vm = require('vm');

const path = 'outputs/2026_Fantasy_Draft_Day_Board_v3.html';
const html = fs.readFileSync(path, 'utf8');
const originalScript = html.slice(html.indexOf('<script>') + 8, html.indexOf('</script>'));
const script = originalScript.replace(
  /render\(\);\s*\}\)\(\);\s*$/,
  "globalThis.__test={players,user,setState,undo,chooseFive,chooseTen,draftInfo,availablePlayers,teamPlayers,rosterAssignment,render,rebuildPlayers,rankingPackage,mockNextPick,byeConflict,byeWeek};render();})();"
);

class FakeElement {
  constructor(id = '') {
    this.id = id;
    this.value = id === 'currentPick' ? '1' : ['positionFilter', 'draftPositionFilter'].includes(id) ? 'ALL' : id === 'stateFilter' ? 'available' : '';
    this.textContent = '';
    this.innerHTML = '';
    this.dataset = {};
    this.files = [];
    this.handlers = {};
    this.classList = { toggle() {} };
  }
  addEventListener(type, handler) { this.handlers[type] = handler; }
  appendChild() {}
  remove() {}
  click() {}
  closest() { return null; }
}

function createContext() {
  const elements = new Map();
  const document = {
    body: new FakeElement('body'),
    getElementById(id) {
      if (!elements.has(id)) elements.set(id, new FakeElement(id));
      return elements.get(id);
    },
    querySelectorAll() { return []; },
    createElement() { return new FakeElement(); },
    addEventListener() {},
  };
  const storage = new Map();
  const context = {
    document,
    localStorage: {
      getItem: key => storage.get(key) || null,
      setItem: (key, value) => storage.set(key, value),
      removeItem: key => storage.delete(key),
    },
    console,
    Blob: class Blob {},
    URL: { createObjectURL: () => 'blob:test', revokeObjectURL() {} },
    setTimeout: callback => callback(),
    confirm: () => true,
    Date,
  };
  vm.createContext(context);
  vm.runInContext(script, context);
  return { context, test: context.__test, elements, storage };
}

function snakePick(position, round) {
  return (round - 1) * 12 + (round % 2 ? position : 13 - position);
}

function simulate(position) {
  const { test, elements } = createContext();
  test.user.position = position;
  test.user.currentPick = 1;
  const myPicks = new Set(Array.from({ length: 13 }, (_, index) => snakePick(position, index + 1)));
  let minimumRecommendations = 99;
  for (let overall = 1; overall <= 156; overall += 1) {
    const cards = test.chooseTen(test.draftInfo());
    minimumRecommendations = Math.min(minimumRecommendations, cards.length);
    const selected = myPicks.has(overall) ? cards[0].player : test.availablePlayers()[0];
    test.setState(selected, myPicks.has(overall) ? 'mine' : 'gone');
  }
  const team = test.teamPlayers();
  const positionCounts = team.reduce((counts, player) => {
    counts[player.p] = (counts[player.p] || 0) + 1;
    return counts;
  }, {});
  if (team.length !== 13) throw new Error(`Slot ${position}: expected 13 team players, got ${team.length}`);
  if (minimumRecommendations !== 10) throw new Error(`Slot ${position}: recommendation count fell to ${minimumRecommendations}`);
  if (!test.draftInfo().complete) throw new Error(`Slot ${position}: draft did not complete`);
  const visibleTeamChips = (elements.get('teamNames').innerHTML.match(/class="team-chip"/g) || []).length;
  if (visibleTeamChips !== 13) throw new Error(`Slot ${position}: persistent team strip shows ${visibleTeamChips} of 13 players`);
  if ((positionCounts.QB || 0) < 1 || (positionCounts.RB || 0) < 2 || (positionCounts.WR || 0) < 2 || (positionCounts.DEF || 0) < 1) {
    throw new Error(`Slot ${position}: invalid starting roster ${JSON.stringify(positionCounts)}`);
  }
  if ((positionCounts.RB || 0) + (positionCounts.WR || 0) + (positionCounts.TE || 0) < 7) {
    throw new Error(`Slot ${position}: fewer than seven RB/WR/TE starters`);
  }
  return { position, positionCounts, first: team[0].n, last: team[12].n };
}

function testUndo() {
  const { test } = createContext();
  test.user.position = 6;
  const player = test.availablePlayers()[0];
  test.setState(player, 'mine');
  if (test.teamPlayers().length !== 1 || test.user.currentPick !== 2) throw new Error('Mine action failed');
  test.undo();
  if (test.teamPlayers().length !== 0 || test.user.currentPick !== 1) throw new Error('Undo failed');
}

function testRankingIsolation() {
  const { test } = createContext();
  const player = test.availablePlayers()[0];
  test.setState(player, 'mine');
  const stateBefore = JSON.stringify(test.user);
  test.rebuildPlayers();
  if (JSON.stringify(test.user) !== stateBefore) throw new Error('Ranking rebuild changed user draft data');
  if (test.teamPlayers()[0].n !== player.n) throw new Error('Team did not survive ranking rebuild');
}

function testMockDraft(position) {
  const { test } = createContext();
  test.user.position = position;
  test.user.currentPick = 1;
  for (let round = 1; round <= 13; round += 1) test.mockNextPick();
  const team = test.teamPlayers();
  if (team.length !== 13 || !test.draftInfo().complete) throw new Error(`Mock slot ${position}: incomplete draft`);
  const counts = team.reduce((result, player) => ({ ...result, [player.p]: (result[player.p] || 0) + 1 }), {});
  if ((counts.QB || 0) < 1 || (counts.QB || 0) > 2 || (counts.RB || 0) < 2 || (counts.WR || 0) < 2 || (counts.DEF || 0) !== 1) throw new Error(`Mock slot ${position}: invalid roster ${JSON.stringify(counts)}`);
  const finalUserPick = snakePick(position, 13);
  if (test.user.history.length !== finalUserPick) throw new Error(`Mock slot ${position}: expected ${finalUserPick} simulated selections`);
  test.undo();
  if (test.teamPlayers().length !== 12) throw new Error(`Mock slot ${position}: grouped undo did not remove one mock pick`);
  test.mockNextPick();
  if (test.teamPlayers().length !== 13 || !test.draftInfo().complete) throw new Error(`Mock slot ${position}: replay after undo failed`);
}

function testAllViewRecommendations() {
  const { test, elements } = createContext();
  test.user.position = 6;
  test.render();
  const allView = elements.get('allList').innerHTML;
  const labels = test.chooseTen(test.draftInfo()).map(card => card.label);
  let previous = -1;
  labels.forEach(label => {
    const index = allView.indexOf(label);
    if (index < 0 || index < previous) throw new Error(`All view missing or misordered ${label}`);
    previous = index;
  });
}

function testByeConflicts() {
  const { test } = createContext();
  const gibbs = test.players.find(player => player.n === 'Jahmyr Gibbs');
  const pacheco = test.players.find(player => player.n === 'Isiah Pacheco');
  test.setState(gibbs, 'mine');
  const conflict = test.byeConflict(pacheco);
  if (conflict.week !== 6 || conflict.sameBye !== 1 || conflict.samePosition !== 1 || conflict.penalty <= 0) throw new Error('Bye-week conflict calculation failed');
}

function testMainDraftBoard() {
  const { test, elements } = createContext();
  test.user.position = 6;
  test.render();
  let board = elements.get('draftBoard').innerHTML;
  if ((board.match(/class="player-row"/g) || []).length !== 40) throw new Error('Main draft board does not show 40 available players');
  test.chooseTen(test.draftInfo()).forEach(card => {
    if (!board.includes(card.label)) throw new Error(`Main draft board is missing ${card.label}`);
  });
  const removed = test.availablePlayers()[0];
  test.setState(removed, 'gone');
  board = elements.get('draftBoard').innerHTML;
  if (board.includes(`data-key="${removed.k}"`)) throw new Error('Gone player remained on main draft board');
  if ((board.match(/class="player-row"/g) || []).length !== 40) throw new Error('Main draft board did not refill after a player was taken');
}

const results = [simulate(1), simulate(6), simulate(12)];
testUndo();
testRankingIsolation();
[1, 6, 12].forEach(testMockDraft);
testAllViewRecommendations();
testByeConflicts();
testMainDraftBoard();
console.log(JSON.stringify(results, null, 2));
console.log('PASS: exactly ten team-first recommendations throughout all simulated drafts');
console.log('PASS: 13 selected players remain visible on My Team');
console.log('PASS: undo and ranking/user-data isolation work');
console.log('PASS: one-click mock picks and grouped undo work from slots 1, 6, and 12');
console.log('PASS: All Players begins with the same labeled Top 10 recommendations');
console.log('PASS: official 2026 bye weeks produce team and position conflict penalties');
console.log('PASS: main-screen board shows 40 players and removes Gone picks immediately');
