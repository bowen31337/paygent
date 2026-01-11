📌 Step-by-Step: Deploy VVS Contracts to Cronos Testnet

This example uses Hardhat, a popular Ethereum/EVM dev framework.

✅ 1) Clone the VVS Contract Repos
git clone https://github.com/vvs-finance/vvs-swap-core.git
git clone https://github.com/vvs-finance/vvs-swap-periphery.git


Navigate into vvs-swap-core first.

✅ 2) Install Dependencies
cd vvs-swap-core
npm install


Then repeat in the periphery folder:

cd ../vvs-swap-periphery
npm install

✅ 3) Set Up Hardhat

If there isn’t a Hardhat config, create one:

npx hardhat init


Modify hardhat.config.js like:

require("@nomiclabs/hardhat-ethers");
module.exports = {
  solidity: "0.7.6",
  networks: {
    cronosTestnet: {
      url: "https://evm-t3.cronos.org/",
      chainId: 338,
      accounts: [process.env.DEPLOYER_PRIVATE_KEY]
    }
  }
};


Store your private key in .env and load it via dotenv for safety.

✅ 4) Compile the Contracts

In each repo:

npx hardhat compile

✅ 5) Write a Deployment Script

Example deploy.js:

async function main() {
  const [deployer] = await ethers.getSigners();
  console.log("Deploying from", deployer.address);

  const Factory = await ethers.getContractFactory("VVSV3Factory");
  const factory = await Factory.deploy(deployer.address);
  await factory.deployed();
  console.log("Factory:", factory.address);

  const Router = await ethers.getContractFactory("VVSV3Router");
  const router = await Router.deploy(factory.address, WRAPPED_TOKEN_ADDRESS);
  await router.deployed();
  console.log("Router:", router.address);
}

main()
  .then(() => process.exit(0))
  .catch(error => {
     console.error(error);
     process.exit(1);
  });


Replace WRAPPED_TOKEN_ADDRESS with a testnet wrapped token (WCRO) if available — otherwise deploy a dummy token first.

✅ 6) Deploy to Cronos Testnet
npx hardhat run scripts/deploy.js --network cronosTestnet


This will output deployed addresses for each contract.

✅ 7) Verify & Interact

Once deployed:

View them on a Cronos testnet explorer (e.g., CronosScan testnet).

Interact via Hardhat console or using ethers.js/web3.

🧪 Testing / Next Steps

After you deploy contracts:

✔ Add liquidity pairs
✔ Try swaps via a frontend or script
✔ Write tests to ensure everything behaves on testnet
✔ Optionally set up a local fork or Ganache simulation