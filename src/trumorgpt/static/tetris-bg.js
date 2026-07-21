/**
 * 1:1 Cognee.ai Style Ambient Tetris Canvas Engine
 * Features:
 * - Pitch Black Background (#000000)
 * - Bright, crisp white grid lines (rgba(255, 255, 255, 0.18))
 * - Tetromino blocks in shades of dark charcoal gray and deep muted purple with clear white borders
 * - Fast smooth falling animation (240ms step interval)
 */

(function () {
    const CELL_SIZE = 40; // 40px grid cells

    // 7 Standard Tetromino Matrix Definitions
    const TETROMINO_SHAPES = {
        I: [[1, 1, 1, 1]],
        O: [[1, 1], [1, 1]],
        T: [[0, 1, 0], [1, 1, 1]],
        L: [[1, 0], [1, 0], [1, 1]],
        J: [[0, 1], [0, 1], [1, 1]],
        S: [[0, 1, 1], [1, 1, 0]],
        Z: [[1, 1, 0], [0, 1, 1]]
    };

    // Cognee.ai Color Palette: Muted Deep Purples & Dark Charcoal Grays with Bright Crisp Borders
    const COGNEE_PALETTES = [
        { fillTop: '#362C4A', fillBottom: '#272036', stroke: 'rgba(255, 255, 255, 0.25)' }, // Deep Purple
        { fillTop: '#2A2438', fillBottom: '#1F1A2B', stroke: 'rgba(255, 255, 255, 0.22)' }, // Dark Muted Violet
        { fillTop: '#24242B', fillBottom: '#1A1A20', stroke: 'rgba(255, 255, 255, 0.20)' }, // Slate Gray
        { fillTop: '#1E1E24', fillBottom: '#141418', stroke: 'rgba(255, 255, 255, 0.18)' }, // Dark Charcoal
        { fillTop: '#3B3052', fillBottom: '#2D2440', stroke: 'rgba(255, 255, 255, 0.28)' }  // Purple Accent
    ];

    const SHAPE_NAMES = ['I', 'O', 'T', 'L', 'J', 'S', 'Z'];

    let canvas, ctx;
    let cols = 0, rows = 0;
    let activePieces = [];
    let lastStepTime = 0;
    const STEP_INTERVAL = 240; // Fast step interval (240ms)

    function initCanvas() {
        canvas = document.getElementById('background-canvas');
        if (!canvas) return;

        ctx = canvas.getContext('2d');
        resize();
        window.addEventListener('resize', resize);

        // Initial spawn of pieces across screen
        for (let i = 0; i < 8; i++) {
            spawnPiece(true);
        }

        requestAnimationFrame(gameLoop);
    }

    function resize() {
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;
        cols = Math.ceil(canvas.width / CELL_SIZE);
        rows = Math.ceil(canvas.height / CELL_SIZE);
    }

    function spawnPiece(randomY = false) {
        const name = SHAPE_NAMES[Math.floor(Math.random() * SHAPE_NAMES.length)];
        const shape = TETROMINO_SHAPES[name];
        const palette = COGNEE_PALETTES[Math.floor(Math.random() * COGNEE_PALETTES.length)];
        
        const shapeWidth = shape[0].length;
        const maxCol = Math.max(0, cols - shapeWidth);
        const col = Math.floor(Math.random() * (maxCol + 1));
        
        const pieceRows = shape.length;
        const startRow = randomY ? Math.floor(Math.random() * Math.max(1, rows - pieceRows)) : -pieceRows;

        activePieces.push({
            shape,
            palette,
            col,
            row: startRow
        });
    }

    function gameLoop(timestamp) {
        if (!lastStepTime) lastStepTime = timestamp;
        const delta = timestamp - lastStepTime;

        if (delta > STEP_INTERVAL) {
            updateGrid();
            lastStepTime = timestamp;
        }

        draw();
        requestAnimationFrame(gameLoop);
    }

    function updateGrid() {
        for (let i = activePieces.length - 1; i >= 0; i--) {
            const p = activePieces[i];
            p.row += 1;

            // Despawn condition when passing bottom boundary
            if (p.row > rows) {
                activePieces.splice(i, 1);
            }
        }

        // Maintain 7 to 10 active falling shapes
        if (activePieces.length < 9 && Math.random() < 0.7) {
            spawnPiece(false);
        }
    }

    function draw() {
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        // 1. Draw Brighter, Whiter Grid Lines (rgba(255, 255, 255, 0.18))
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.18)';
        ctx.lineWidth = 1;

        ctx.beginPath();
        for (let x = 0; x <= canvas.width; x += CELL_SIZE) {
            ctx.moveTo(x, 0);
            ctx.lineTo(x, canvas.height);
        }
        for (let y = 0; y <= canvas.height; y += CELL_SIZE) {
            ctx.moveTo(0, y);
            ctx.lineTo(canvas.width, y);
        }
        ctx.stroke();

        // 2. Draw Cognee Gray/Purple Flat Tetrominoes with Whiter Cell Borders
        activePieces.forEach(p => {
            const shape = p.shape;
            const palette = p.palette;

            for (let r = 0; r < shape.length; r++) {
                for (let c = 0; c < shape[r].length; c++) {
                    if (shape[r][c] === 1) {
                        const drawCol = p.col + c;
                        const drawRow = p.row + r;

                        if (drawRow >= 0 && drawRow < rows) {
                            const x = drawCol * CELL_SIZE;
                            const y = drawRow * CELL_SIZE;

                            ctx.save();
                            
                            // Linear gradient fill matching Cognee block depth
                            const grad = ctx.createLinearGradient(x, y, x, y + CELL_SIZE);
                            grad.addColorStop(0, palette.fillTop);
                            grad.addColorStop(1, palette.fillBottom);

                            ctx.fillStyle = grad;
                            ctx.fillRect(x, y, CELL_SIZE, CELL_SIZE);

                            // Draw bright white cell border
                            ctx.strokeStyle = palette.stroke;
                            ctx.lineWidth = 1;
                            ctx.strokeRect(x, y, CELL_SIZE, CELL_SIZE);

                            ctx.restore();
                        }
                    }
                }
            }
        });
    }

    document.addEventListener('DOMContentLoaded', initCanvas);
})();
