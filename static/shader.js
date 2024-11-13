const vertexShader = `
    varying vec2 vUv;
    void main() {
        vUv = uv;
        gl_Position = vec4(position, 1.0);
    }
`;

const fragmentShader = `
    uniform float time;
    varying vec2 vUv;
    
    void main() {
        vec2 uv = vUv;
        
        // Create organic, flowing patterns
        float pattern = sin(uv.x * 10.0 + time * 0.3) * 
                       cos(uv.y * 8.0 + time * 0.2) *
                       sin((uv.x + uv.y) * 5.0 + time * 0.4);
        
        // Soft, natural colors
        vec3 color1 = vec3(0.7, 0.9, 0.8);  // Soft sage
        vec3 color2 = vec3(0.9, 0.85, 0.7); // Warm cream
        
        vec3 finalColor = mix(color1, color2, pattern * 0.5 + 0.5);
        
        gl_FragColor = vec4(finalColor, 0.3); // Keep it subtle with low opacity
    }
`;

function initShader() {
    const canvas = document.getElementById('shader-canvas');
    const renderer = new THREE.WebGLRenderer({ canvas, alpha: true });
    const scene = new THREE.Scene();
    const camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);
    
    const material = new THREE.ShaderMaterial({
        vertexShader,
        fragmentShader,
        uniforms: {
            time: { value: 0 }
        },
        transparent: true
    });
    
    const plane = new THREE.PlaneGeometry(2, 2);
    const mesh = new THREE.Mesh(plane, material);
    scene.add(mesh);
    
    function animate(time) {
        material.uniforms.time.value = time * 0.001;
        renderer.render(scene, camera);
        requestAnimationFrame(animate);
    }
    
    function resize() {
        renderer.setSize(window.innerWidth, window.innerHeight);
    }
    
    window.addEventListener('resize', resize);
    resize();
    animate(0);
}

// Load Three.js from CDN and initialize
const script = document.createElement('script');
script.src = 'https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js';
script.onload = initShader;
document.head.appendChild(script); 