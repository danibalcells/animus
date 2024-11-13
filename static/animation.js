class Blob {
    constructor(canvas, size = 'medium') {
        this.x = canvas.width * Math.random();
        this.y = canvas.height * Math.random();
        
        // Size ranges for different blob types
        const sizes = {
            small: 20 + Math.random() * 30,    // 20-50
            medium: 40 + Math.random() * 60,   // 40-100
            large: 100 + Math.random() * 100   // 100-200
        };
        
        this.radius = sizes[size];
        this.xSpeed = 0.8 - Math.random() * 1.6;
        this.ySpeed = 0.8 - Math.random() * 1.6;
        this.phase = Math.random() * Math.PI * 2;
    }

    update(canvas) {
        this.phase += 0.008;
        this.x += Math.sin(this.phase) * this.xSpeed;
        this.y += Math.cos(this.phase) * this.ySpeed;
        
        // Wrap around edges
        if (this.x < -100) this.x = canvas.width + 100;
        if (this.x > canvas.width + 100) this.x = -100;
        if (this.y < -100) this.y = canvas.height + 100;
        if (this.y > canvas.height + 100) this.y = -100;
    }
}

const canvas = document.createElement('canvas');
const ctx = canvas.getContext('2d');
document.body.appendChild(canvas);
canvas.style.position = 'fixed';
canvas.style.top = '0';
canvas.style.left = '0';
canvas.style.width = '100%';
canvas.style.height = '100%';
canvas.style.zIndex = '-1';

let blobs = [];
let time = 0;

function resize() {
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
    
    // Reset blobs with different sizes
    blobs = [
        // Large blobs (fewer)
        ...Array.from({ length: 2 }, () => new Blob(canvas, 'large')),
        // Medium blobs
        ...Array.from({ length: 4 }, () => new Blob(canvas, 'medium')),
        // Small blobs
        ...Array.from({ length: 6 }, () => new Blob(canvas, 'small'))
    ];
}

function draw() {
    ctx.fillStyle = 'rgb(0, 0, 0)';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    
    // Update blob positions
    blobs.forEach(blob => blob.update(canvas));

    const imageData = ctx.createImageData(canvas.width, canvas.height);
    const data = imageData.data;
    
    for (let x = 0; x < canvas.width; x += 2) {
        for (let y = 0; y < canvas.height; y += 2) {
            let sum = 0;
            
            blobs.forEach(blob => {
                const dx = x - blob.x;
                const dy = y - blob.y;
                const distance = Math.sqrt(dx * dx + dy * dy);
                sum += (blob.radius * blob.radius) / (distance * distance);
            });
            
            const index = (x + y * canvas.width) * 4;
            const intensity = Math.min(sum, 1);
            
            // Purple-ish lava color
            data[index] = 25 * intensity;     // R
            data[index + 1] = 0;              // G
            data[index + 2] = 35 * intensity; // B
            data[index + 3] = 255;            // A
            
            // Fill adjacent pixels for performance
            if (x < canvas.width - 1 && y < canvas.height - 1) {
                const right = index + 4;
                const bottom = index + (canvas.width * 4);
                const bottomRight = bottom + 4;
                
                [right, bottom, bottomRight].forEach(idx => {
                    data[idx] = data[index];
                    data[idx + 1] = data[index + 1];
                    data[idx + 2] = data[index + 2];
                    data[idx + 3] = data[index + 3];
                });
            }
        }
    }
    
    ctx.putImageData(imageData, 0, 0);
    
    time += 0.01;
    requestAnimationFrame(draw);
}

window.addEventListener('resize', resize);
resize();
draw(); 